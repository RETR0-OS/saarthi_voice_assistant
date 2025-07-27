import threading
import streamlit as st
from ..identity_wallet.identity_manager.identity_manager import IdentityManager

class IdentityManagerSingleton:
    """
    Singleton wrapper for IdentityManager to ensure only one instance exists.
    This reduces the high overhead of creating multiple IdentityManager instances.
    """
    _instance = None
    _lock = threading.Lock()
    _identity_manager = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(IdentityManagerSingleton, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if self._identity_manager is None:
            with self._lock:
                if self._identity_manager is None:
                    self._identity_manager = IdentityManager(camera_id=1)

    def __getattr__(self, name):
        """Delegate all attribute access to the wrapped IdentityManager instance"""
        return getattr(self._identity_manager, name)

    def __setattr__(self, name, value):
        """Delegate attribute setting to the wrapped IdentityManager instance"""
        if name in ['_instance', '_lock', '_identity_manager']:
            # These are singleton-specific attributes
            super().__setattr__(name, value)
        else:
            # Delegate to the wrapped instance
            if hasattr(self, '_identity_manager') and self._identity_manager is not None:
                setattr(self._identity_manager, name, value)
            else:
                super().__setattr__(name, value)

    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing or cleanup)"""
        with cls._lock:
            if cls._instance and cls._instance._identity_manager:
                cls._instance._identity_manager.logout()
            cls._instance = None
            cls._identity_manager = None

def get_identity_manager():
    """
    Get IdentityManager instance from Streamlit session state.
    This ensures the instance and its keys persist across Streamlit interactions.
    """
    if 'identity_manager_instance' not in st.session_state:
        st.session_state.identity_manager_instance = IdentityManager(camera_id=1)
    return st.session_state.identity_manager_instance

def reset_identity_manager():
    """
    Reset the IdentityManager instance in session state.
    Call this during logout to properly clean up.
    """
    if 'identity_manager_instance' in st.session_state:
        # Logout and cleanup the current instance
        st.session_state.identity_manager_instance.logout()
        # Remove from session state
        del st.session_state.identity_manager_instance
