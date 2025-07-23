import keyring
import base64
from typing import Optional

class SecureKeyManager:
    """Manages wrapping keys using Windows Credential Manager (hardware-backed secure storage)"""

    SERVICE_NAME = "Saarthi_IdentityVault"

    @staticmethod
    def _get_key_name(user_id: str) -> str:
        """Generate a unique key name for the user"""
        return f"{SecureKeyManager.SERVICE_NAME}_{user_id}_wrapping_key"

    @staticmethod
    def store_wrapping_key(user_id: str, wrapping_key: bytes) -> bool:
        """
        Store wrapping key in Windows Credential Manager
        Returns True if successful, False otherwise
        """
        try:
            # Convert bytes to base64 string for storage
            key_b64 = base64.b64encode(wrapping_key).decode('utf-8')
            key_name = SecureKeyManager._get_key_name(user_id)

            # Store in Windows Credential Manager
            keyring.set_password(SecureKeyManager.SERVICE_NAME, key_name, key_b64)
            return True
        except Exception as e:
            print(f"Failed to store wrapping key: {e}")
            return False

    @staticmethod
    def retrieve_wrapping_key(user_id: str) -> Optional[bytes]:
        """
        Retrieve wrapping key from Windows Credential Manager
        Returns the key bytes or None if not found
        """
        try:
            key_name = SecureKeyManager._get_key_name(user_id)
            key_b64 = keyring.get_password(SecureKeyManager.SERVICE_NAME, key_name)

            if key_b64:
                # Convert base64 string back to bytes
                return base64.b64decode(key_b64.encode('utf-8'))
            return None
        except Exception as e:
            print(f"Failed to retrieve wrapping key: {e}")
            return None

    @staticmethod
    def delete_wrapping_key(user_id: str) -> bool:
        """
        Delete wrapping key from Windows Credential Manager
        Returns True if successful, False otherwise
        """
        try:
            key_name = SecureKeyManager._get_key_name(user_id)
            keyring.delete_password(SecureKeyManager.SERVICE_NAME, key_name)
            return True
        except Exception as e:
            print(f"Failed to delete wrapping key: {e}")
            return False
