import os
import sqlite3
from ..models.User import User
from typing import Optional, Dict, Any, List


class DatabaseManager:
    """Handles database operations for user data and encrypted keys"""

    def __init__(self, db_path: str = "identity_vault.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables"""
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path))
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Users table with face templates and encrypted KEKs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NULL,
                    dob TEXT NOT NULL,
                    phone INTEGER NOT NULL,
                    face_embedding BLOB NOT NULL,
                    encrypted_kek BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # PII data table with encrypted DEKs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    encrypted_data BLOB NOT NULL,
                    encrypted_dek BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            conn.commit()

    def store_user(self, user: User, face_embedding: bytes, encrypted_kek: bytes):
        """Store user enrollment data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (user_id, first_name, last_name, dob, phone, face_embedding, encrypted_kek)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user._id, user.first_name, user.last_name, user.dob, user.phone, face_embedding, encrypted_kek))
            conn.commit()

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user data by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, first_name, last_name, dob, phone, face_embedding, encrypted_kek
                FROM users WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()

            if row:
                return {
                    'user_id': row[0],
                    'first_name': row[1],
                    'last_name': row[2],
                    'dob': row[3],
                    'phone': row[4],
                    'face_embedding': row[5],
                    'encrypted_kek': row[6]
                }
            return None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users for face matching during login"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, first_name, last_name, dob, phone, face_embedding, encrypted_kek
                FROM users
            ''')
            rows = cursor.fetchall()

            return [{
                'user_id': row[0],
                'first_name': row[1],
                'last_name': row[2],
                'dob': row[3],
                'phone': row[4],
                'face_embedding': row[5],
                'encrypted_kek': row[6]
            } for row in rows]
        
    def get_all_data_types(self, user_id: str) -> List[str]:
        """Get all available data types for the given user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT data_type FROM user_data WHERE user_id = ?
            ''', (user_id,))
            rows = cursor.fetchall()
            return list(rows)

    def store_encrypted_data(self, user_id: str, data_type: str, encrypted_data: bytes, encrypted_dek: bytes):
        """Store encrypted PII data with encrypted DEK"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_data (user_id, data_type, encrypted_data, encrypted_dek)
                VALUES (?, ?, ?, ?)
            ''', (user_id, data_type, encrypted_data, encrypted_dek))
            conn.commit()

    def get_encrypted_data(self, user_id: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve encrypted data and DEK"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT encrypted_data, encrypted_dek
                FROM user_data WHERE user_id = ? AND data_type = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (user_id, data_type))
            row = cursor.fetchone()

            if row:
                return {
                    'encrypted_data': row[0],
                    'encrypted_dek': row[1]
                }
            return None
