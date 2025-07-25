import secrets
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from typing import List

class CryptoManager:
    """Handles all cryptographic operations for the identity vault"""

    @staticmethod
    def generate_key() -> bytes:
        """Generate a secure random 256-bit key"""
        return secrets.token_bytes(32)

    @staticmethod
    def encrypt_with_key(data: bytes, key: bytes) -> bytes:
        """Encrypt data using AES-256-GCM"""
        # Generate a random 96-bit IV for GCM
        iv = secrets.token_bytes(12)
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        # Return IV + tag + ciphertext
        return iv + encryptor.tag + ciphertext

    @staticmethod
    def decrypt_with_key(encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt data using AES-256-GCM"""
        # Extract IV (12 bytes), tag (16 bytes), and ciphertext
        iv = encrypted_data[:12]
        tag = encrypted_data[12:28]
        ciphertext = encrypted_data[28:]

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    @staticmethod
    def serialize_embedding(embedding: List[float]) -> bytes:
        """Convert face embedding to bytes for storage"""
        return json.dumps(embedding).encode('utf-8')

    @staticmethod
    def deserialize_embedding(data: bytes) -> List[float]:
        """Convert bytes back to face embedding"""
        return json.loads(data.decode('utf-8'))
