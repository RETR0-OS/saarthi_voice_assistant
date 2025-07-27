import sqlite3
import hashlib

from typing import Optional, Dict, Any, List
import numpy as np
import uuid
import appdirs
import os

from ..utilities.identity_db_manager import DatabaseManager
from ..models.User import User
from ..identity_manager.face_recognition import FaceRecognitionUtility, CameraManager
from ..utilities.crypto_manager import CryptoManager
from ..utilities.key_manager import SecureKeyManager
import os
from dotenv import load_dotenv

load_dotenv()

import traceback


class IdentityManager:
    """Main identity management class implementing the face-gated identity vault"""

    def __init__(self, camera_id: int = int(os.getenv("CAMERA_ID", 0))):
        db_path = os.path.join(appdirs.user_data_dir("Saarthi", "AlgoHackers"), "identity_vault.db")
        self.is_logged_in = False
        self.current_user = None
        self.camera_manager = CameraManager(camera_id=camera_id)
        self.db_manager = DatabaseManager(db_path)

        # Session-only memory (wiped on logout/close)
        self._wrapping_key: Optional[bytes] = None
        self._kek: Optional[bytes] = None
        self._session_active = False

    def _generate_user_id(self, name: str) -> str:
        """Generate a unique user ID based on name and timestamp and a uuid"""
        import time
        timestamp = str(int(time.time()))
        random_id = str(uuid.uuid4())[:8]
        return hashlib.sha256(f"{name}_{timestamp}_{random_id}".encode()).hexdigest()[:16]

    def _compare_face_embeddings(self, embedding1: np.ndarray, embedding2: np.ndarray) -> bool:
        """Compare two face embeddings using cosine similarity"""
        try:
            return FaceRecognitionUtility.match_embeddings(embedding1, embedding2)
        except Exception as e:
            print("Error comparing face embeddings:", e)
            return False

    def capture_frames(self):
        """Capture frames from camera"""
        return self.camera_manager.get_frames()

    def add_user(self, first_name: str, dob: str, phone: int, last_name:Optional[str] = None) -> Dict[str, Any]:
        """
        Enrollment process: Capture face, generate keys, and store securely
        """
        try:
            # Step 1: Capture User's Face
            frames = self.capture_frames()
            if not frames:
                return {"result": False, "error": "Failed to capture frames from camera"}

            validation_result = FaceRecognitionUtility.verify_embeddings(list(frames))

            if not validation_result["result"]:
                return {"result": False, "error": validation_result["error"]}

            # Step 2: Generate Key Encryption Key (KEK)
            kek = CryptoManager.generate_key()

            # Step 3: Generate random wrapping key (will be stored in hardware-backed secure storage)
            wrapping_key = CryptoManager.generate_key()

            # Step 4: Encrypt KEK with Wrapping Key
            encrypted_kek = CryptoManager.encrypt_with_key(kek, wrapping_key)

            # Step 5: Store Face Template and Encrypted KEK
            name = f"{first_name} {last_name}" if last_name else first_name
            user_id = self._generate_user_id(name)
            face_embedding_bytes = CryptoManager.serialize_embedding(validation_result["embedding"])

            user = User(_id=user_id, first_name=first_name, last_name=last_name, dob=dob, phone=phone)
            self.db_manager.store_user(user, face_embedding_bytes, encrypted_kek)

            # Step 6: Store wrapping key securely in Windows Credential Manager
            if not SecureKeyManager.store_wrapping_key(user_id, wrapping_key):
                return {"result": False, "error": "Failed to securely store wrapping key"}

            # Store keys in session memory
            self._wrapping_key = wrapping_key
            self._kek = kek
            self._session_active = True

            # Create User object
            self.current_user = user
            self.is_logged_in = True

            return {
                "result": True,
                "user_id": user_id,
                "message": f"User {name} enrolled successfully"
            }

        except Exception as e:
            return {"result": False, "error": f"Enrollment failed: {str(e)}"}

    def login(self) -> Dict[str, Any]:
        """
        Authentication process: Capture face, match against stored templates, decrypt KEK
        """
        try:
            # Step 1: Capture Live Face
            frames = self.capture_frames()
            if not frames:
                return {"result": False, "error": "Failed to capture frames from camera"}

            validation_result = FaceRecognitionUtility.verify_embeddings(list(frames))

            if not validation_result["result"]:
                return {"result": False, "error": validation_result["error"]}

            live_embedding = validation_result["embedding"]

            # Step 2: Compare to Stored Templates
            all_users = self.db_manager.get_all_users()
            matched_user = None

            for user_data in all_users:
                stored_embedding = CryptoManager.deserialize_embedding(user_data['face_embedding'])

                if self._compare_face_embeddings(live_embedding, stored_embedding):
                    matched_user = user_data
                    break

            if not matched_user:
                return {"result": False, "error": "Face not recognized"}

            # Step 3: Retrieve wrapping key from secure hardware storage
            wrapping_key = SecureKeyManager.retrieve_wrapping_key(matched_user['user_id'])
            if not wrapping_key:
                return {"result": False, "error": "Failed to retrieve secure key - user may need to re-enroll"}

            self._wrapping_key = wrapping_key

            # Step 4: Decrypt the KEK using the retrieved wrapping key
            try:
                self._kek = CryptoManager.decrypt_with_key(matched_user['encrypted_kek'], self._wrapping_key)
            except Exception as e:
                return {"result": False, "error": f"Key decryption failed: {str(e)}"}

            # Load KEK into memory for session
            self._session_active = True

            # Create User object
            user = User(_id=matched_user['user_id'], first_name=matched_user['first_name'], last_name=matched_user['last_name'], dob=matched_user['dob'], phone=matched_user['phone'])
            self.current_user = user
            self.is_logged_in = True

            return {
                "result": True,
                "user_id": matched_user['user_id'],
                "message": f"Welcome back, {matched_user['first_name']}!"
            }

        except Exception as e:
            return {"result": False, "error": f"Login failed: {str(e)}"}

    def logout(self):
        """
        Session cleanup: Wipe keys from memory
        """
        # Step 5: Session Handling - Wipe memory
        self._wrapping_key = None
        self._kek = None
        self._session_active = False
        self.current_user = None
        self.is_logged_in = False

        # Release camera resources
        self.camera_manager.release()

    def verify_user(self) -> bool:
        """
        Verify if user is authenticated and session is active
        """
        return self.is_logged_in and self._session_active and self._kek is not None

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current user
        """
        if not self.verify_user():
            return None

        return {
            "user_id": self.current_user._id,
            "name": self.current_user.first_name + (" " + self.current_user.last_name if self.current_user.last_name else ""),
            "is_authenticated": True
        }

    def encrypt_pii_data(self, data_type: str, pii_data: str) -> Dict[str, Any]:
        """
        PII Encryption: Generate DEK, encrypt data, encrypt DEK with KEK
        """
        if not self.verify_user():
            return {"result": False, "error": "User not authenticated"}

        try:
            # Step 1: Generate Data Encryption Key (DEK)
            dek = CryptoManager.generate_key()

            # Step 2: Encrypt PII data with DEK
            pii_bytes = pii_data.encode('utf-8')
            encrypted_data = CryptoManager.encrypt_with_key(pii_bytes, dek)

            # Step 3: Encrypt DEK with KEK
            encrypted_dek = CryptoManager.encrypt_with_key(dek, self._kek)

            # Step 4: Store encrypted data and encrypted DEK
            self.db_manager.store_encrypted_data(
                self.current_user._id, data_type, encrypted_data, encrypted_dek
            )

            return {
                "result": True,
                "message": f"PII data '{data_type}' encrypted and stored successfully"
            }

        except Exception as e:
            return {"result": False, "error": f"Encryption failed: {str(e)}"}

    def decrypt_pii_data(self, data_type: str) -> Dict[str, Any]:
        """
        PII Decryption: Retrieve encrypted data, decrypt DEK with KEK, decrypt data with DEK
        """
        if not self.verify_user():
            return {"result": False, "error": "User not authenticated"}

        try:
            # Step 1: Retrieve encrypted data and encrypted DEK
            stored_data = self.db_manager.get_encrypted_data(self.current_user._id, data_type)

            if not stored_data:
                return {"result": False, "error": f"No data found for type '{data_type}'"}

            # Step 2: Decrypt DEK with KEK
            dek = CryptoManager.decrypt_with_key(stored_data['encrypted_dek'], self._kek)

            # Step 3: Decrypt data with DEK
            decrypted_bytes = CryptoManager.decrypt_with_key(stored_data['encrypted_data'], dek)
            decrypted_data = decrypted_bytes.decode('utf-8')

            return {
                "result": True,
                "data": decrypted_data,
                "data_type": data_type
            }

        except Exception as e:
            return {"result": False, "error": f"Decryption failed: {str(e)}"}

    def list_encrypted_data_types(self) -> List[str]:
        """
        List all data types stored for the current user
        """
        if not self.verify_user():
            return []

        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT data_type FROM user_data WHERE user_id = ?
            ''', (self.current_user._id,))

            return [row[0] for row in cursor.fetchall()]

    def authenticate_user(self):
        """
        Checks if the user performing an action is the same as the one logged in.
        :return: True if the user is authenticated, False otherwise.
        """

        # capture current face
        frames = self.capture_frames()
        if not frames:
            return False
        validation_result = FaceRecognitionUtility.verify_embeddings(list(frames))
        if not validation_result["result"]:
            return False
        live_embedding = validation_result["embedding"]
        # compare with stored face embedding
        stored_user = self.db_manager.get_user_by_id(self.current_user._id)
        if not stored_user:
            return False
        stored_embedding = CryptoManager.deserialize_embedding(stored_user['face_embedding'])
        return self._compare_face_embeddings(live_embedding, stored_embedding)


    def get_all_pii_keys(self) -> Optional[bytes]:
        """
        Get the available PII data types for the current logged in user
        """
        if not self.verify_user():
            return None
        
        #get all available data types keys for the current user
        user_id = self.current_user._id
        data_types = self.db_manager.get_all_data_types(user_id)
        return data_types
    
    def fetch_user_profile_info(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the user profile information
        """
        if not self.verify_user():
            return None
        return self.current_user.to_dict()

    def __del__(self):
        """Cleanup on destruction"""
        self.logout()
