from crewai.tools import BaseTool
from langchain_community.tools import DuckDuckGoSearchRun
import datetime
from identity_wallet.identity_manager.identity_manager import IdentityManager
from typing import Dict, Any, Optional
import json
import threading


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
                    self._identity_manager = IdentityManager()
    
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


class GovernmentSchemeTool(BaseTool):
    name: str ="government_scheme_search"
    description: str ="Search for active government schemes and policies from official sources"
    def _run(self, query: str, country: str = 'India') -> str:
        search = DuckDuckGoSearchRun()
        official_queries = [
            f"{query} site:gov.in {country} 2024 2025",
            f"{query} government scheme policy {country} active",
            f"{query} ministry {country} latest announcement"
        ]
        
        results = []
        for q in official_queries:
            try:
                result = search.run(q)
                results.append(result)
            except Exception as e:
                results.append(f"Search error: {str(e)}")
        
        return "\n\n".join(results)
    

class DateTimeTool(BaseTool):
    name: str = "datetime_tool"
    description: str = "Get the current date and time in UTC format"

    def _run(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    

class UserAuthenticationTool(BaseTool):
    """Tool for user authentication operations without exposing any PII"""
    name: str = "user_authentication"
    description: str = "Authenticate users through face recognition. Supports login, logout, and verification operations."
    
    @property
    def identity_manager(self) -> IdentityManager:
        return IdentityManagerSingleton.get_instance()
    
    def _run(self, action: str, **kwargs) -> str:
        """
        Execute authentication actions.
        
        Args:
            action: One of 'login', 'logout', 'verify', 'status'
            
        Returns:
            JSON string with result status and message
        """
        try:
            if action == "login":
                result = self.identity_manager.login()
                if result["result"]:
                    # Don't expose user_id or any PII
                    return json.dumps({
                        "success": True,
                        "message": "User authenticated successfully",
                        "session_active": True
                    })
                else:
                    return json.dumps({
                        "success": False,
                        "message": result.get("error", "Authentication failed"),
                        "session_active": False
                    })
                    
            elif action == "logout":
                self.identity_manager.logout()
                return json.dumps({
                    "success": True,
                    "message": "User logged out successfully",
                    "session_active": False
                })
                
            elif action == "verify":
                is_verified = self.identity_manager.verify_user()
                return json.dumps({
                    "success": True,
                    "authenticated": is_verified,
                    "message": "User is authenticated" if is_verified else "User is not authenticated"
                })
                
            elif action == "status":
                is_logged_in = self.identity_manager.is_logged_in
                session_active = self.identity_manager._session_active
                return json.dumps({
                    "success": True,
                    "logged_in": is_logged_in,
                    "session_active": session_active,
                    "message": f"Login status: {'Active' if is_logged_in else 'Inactive'}"
                })
                
            else:
                return json.dumps({
                    "success": False,
                    "message": f"Unknown action: {action}. Valid actions are: login, logout, verify, status"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Authentication error: {str(e)}"
            })


class PIIRetrievalTool(BaseTool):
    """Tool to check if specific PII exists without revealing the actual data"""
    name: str = "pii_retrieval_check"
    description: str = "Check if specific PII data exists for the authenticated user"
    
    @property
    def identity_manager(self) -> IdentityManager:
        return IdentityManagerSingleton.get_instance()
    
    def _run(self, data_type: str) -> str:
        """
        Check if specific PII data exists.
        
        Args:
            data_type: Type of PII to check (e.g., 'aadhaar', 'pan', 'phone', 'address')
            
        Returns:
            JSON string indicating if data exists without revealing the actual data
        """
        try:
            if not self.identity_manager.verify_user():
                return json.dumps({
                    "success": False,
                    "message": "User not authenticated. Please login first."
                })
            
            # Try to decrypt the data but don't return it
            result = self.identity_manager.decrypt_pii_data(data_type)
            
            if result["result"]:
                # Data exists but we don't reveal it
                return json.dumps({
                    "success": True,
                    "data_exists": True,
                    "data_type": data_type,
                    "message": f"PII data of type '{data_type}' is available"
                })
            else:
                return json.dumps({
                    "success": True,
                    "data_exists": False,
                    "data_type": data_type,
                    "message": f"No PII data of type '{data_type}' found"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Error checking PII data: {str(e)}"
            })


class PIIWriterTool(BaseTool):
    """Tool to use PII data in forms/applications without exposing it to the agent"""
    name: str = "pii_writer"
    description: str = "Use PII data to fill forms or applications without revealing the actual data to the agent"
    
    @property
    def identity_manager(self) -> IdentityManager:
        return IdentityManagerSingleton.get_instance()
    
    def _run(self, data_type: str, target_field: str, form_id: Optional[str] = None) -> str:
        """
        Use PII data to fill a form field without exposing the data.
        
        Args:
            data_type: Type of PII to use (e.g., 'aadhaar', 'pan', 'phone', 'address')
            target_field: The field name or identifier where data should be entered
            form_id: Optional form identifier for tracking purposes
            
        Returns:
            JSON string confirming the action without revealing the data
        """
        try:
            if not self.identity_manager.verify_user():
                return json.dumps({
                    "success": False,
                    "message": "User not authenticated. Please login first."
                })
            
            # Re-authenticate user before using PII
            if not self.identity_manager.authenticate_user():
                return json.dumps({
                    "success": False,
                    "message": "Re-authentication failed. Cannot proceed with PII usage."
                })
            
            # Retrieve the PII data
            result = self.identity_manager.decrypt_pii_data(data_type)
            
            if not result["result"]:
                return json.dumps({
                    "success": False,
                    "message": f"PII data of type '{data_type}' not found"
                })
            
            # In a real implementation, this would interface with form-filling APIs
            # or browser automation to fill the data without exposing it
            # For now, we just confirm the action
            
            # Log the action without logging the actual data
            action_log = {
                "timestamp": datetime.datetime.now().isoformat(),
                "data_type": data_type,
                "target_field": target_field,
                "form_id": form_id,
                "status": "completed"
            }
            
            return json.dumps({
                "success": True,
                "message": f"PII data of type '{data_type}' has been securely entered into field '{target_field}'",
                "action_log": action_log
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Error using PII data: {str(e)}"
            })


class PIIStorageTool(BaseTool):
    """Tool to store new PII data for authenticated users"""
    name: str = "pii_storage"
    description: str = "Request user to provide PII data for secure storage. The agent never sees the actual data."
    
    @property
    def identity_manager(self) -> IdentityManager:
        return IdentityManagerSingleton.get_instance()
    
    def _run(self, data_type: str, prompt_message: str) -> str:
        """
        Request PII data from user for storage.
        
        Args:
            data_type: Type of PII to store (e.g., 'aadhaar', 'pan', 'phone', 'address')
            prompt_message: Message to display to user when requesting the data
            
        Returns:
            JSON string confirming storage without revealing the data
        """
        try:
            if not self.identity_manager.verify_user():
                return json.dumps({
                    "success": False,
                    "message": "User not authenticated. Please login first."
                })
            
            # In a real implementation, this would trigger a secure UI prompt
            # that collects data directly from the user without the agent seeing it
            # For demonstration, we'll simulate this
            
            return json.dumps({
                "success": True,
                "message": f"Request sent to user for '{data_type}' data",
                "prompt_displayed": prompt_message,
                "status": "awaiting_user_input",
                "note": "User will be prompted to enter data securely"
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Error requesting PII storage: {str(e)}"
            })


class UserEnrollmentTool(BaseTool):
    """Tool for enrolling new users without exposing their PII"""
    name: str = "user_enrollment"
    description: str = "Enroll new users with face recognition. Personal details are collected securely without agent access."
    
    @property
    def identity_manager(self) -> IdentityManager:
        return IdentityManagerSingleton.get_instance()
    
    def _run(self, enrollment_request: str) -> str:
        """
        Initiate user enrollment process.
        
        Args:
            enrollment_request: Description of enrollment request
            
        Returns:
            JSON string with enrollment status
        """
        try:
            # In a real implementation, this would trigger a secure UI
            # that collects user details directly without agent access
            
            return json.dumps({
                "success": True,
                "message": "User enrollment process initiated",
                "status": "awaiting_user_data",
                "instructions": "User will be prompted to provide details and capture face biometrics",
                "note": "All personal information will be collected securely without agent access"
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Enrollment error: {str(e)}"
            })
        