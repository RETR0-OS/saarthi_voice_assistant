import traceback
from typing import Dict, Any, Optional
import uuid
from .auth_graph import create_auth_graph, set_user_input, clear_user_input

class AuthGraphRunner:
    """Simple interface for running the authentication graph from frontend"""
    
    def __init__(self):
        self.auth_graph = create_auth_graph()
        print(self.auth_graph.get_graph().draw_mermaid())
        self.current_thread_id = None
    
    def start_authentication(self) -> Dict[str, Any]:
        """Start a new authentication session"""
        # Generate new thread ID for this auth session
        self.current_thread_id = f"auth_{uuid.uuid4()}"
        clear_user_input()  # Clear any previous user inputs
        
        try:
            # Run the auth graph
            result = self.auth_graph.invoke(
                {},
                config={"configurable": {"thread_id": self.current_thread_id}}
            )
            
            return {
                "success": True,
                "auth_result": result.get("auth_result", False),
                "notes": result.get("notes", ""),
                "pii_collection_complete": result.get("pii_collection_complete", False),
                "requires_registration": "registration required" in result.get("notes", "").lower(),
                "requires_pii": False  # Will be set by continue_with_registration
            }
        except Exception as e:

            print(traceback.format_exc())

            return {
                "success": False,
                "auth_result": False,
                "notes": f"Authentication failed: {str(e)}",
                "error": str(e)
            }
    
    def continue_with_registration(self, registration_data: Dict[str, str]) -> Dict[str, Any]:
        """Continue authentication with registration data"""
        if not self.current_thread_id:
            return {
                "success": False,
                "auth_result": False,
                "notes": "No active authentication session"
            }
        
        try:
            # Set the registration data for HITL
            set_user_input("registration", registration_data)
            
            # Continue the auth graph execution
            result = self.auth_graph.invoke(
                {},
                config={"configurable": {"thread_id": self.current_thread_id}}
            )
            
            # Check if we need PII collection
            requires_pii = result.get("notes", "").lower().find("pii collection") != -1
            
            return {
                "success": True,
                "auth_result": result.get("auth_result", False),
                "notes": result.get("notes", ""),
                "pii_collection_complete": result.get("pii_collection_complete", False),
                "requires_pii": requires_pii
            }
        except Exception as e:
            return {
                "success": False,
                "auth_result": False,
                "notes": f"Registration failed: {str(e)}",
                "error": str(e)
            }
    
    def continue_with_pii(self, pii_data: Dict[str, str]) -> Dict[str, Any]:
        """Continue authentication with PII data"""
        if not self.current_thread_id:
            return {
                "success": False,
                "auth_result": False,
                "notes": "No active authentication session"
            }
        
        try:
            # Set the PII data for HITL
            set_user_input("pii", pii_data)
            
            # Continue the auth graph execution
            result = self.auth_graph.invoke(
                {},
                config={"configurable": {"thread_id": self.current_thread_id}}
            )
            
            return {
                "success": True,
                "auth_result": result.get("auth_result", False),
                "notes": result.get("notes", ""),
                "pii_collection_complete": result.get("pii_collection_complete", False)
            }
        except Exception as e:
            return {
                "success": False,
                "auth_result": False,
                "notes": f"PII collection failed: {str(e)}",
                "error": str(e)
            }
    
    def reset_session(self):
        """Reset the current authentication session"""
        self.current_thread_id = None
        clear_user_input()

# Global instance for frontend use
auth_runner = AuthGraphRunner()

def run_authentication() -> Dict[str, Any]:
    """Simple function to start authentication - used by frontend"""
    return auth_runner.start_authentication()

def submit_registration_data(registration_data: Dict[str, str]) -> Dict[str, Any]:
    """Submit registration data and continue authentication"""
    return auth_runner.continue_with_registration(registration_data)

def submit_pii_data(pii_data: Dict[str, str]) -> Dict[str, Any]:
    """Submit PII data and complete authentication"""
    return auth_runner.continue_with_pii(pii_data)

def reset_authentication():
    """Reset authentication session"""
    auth_runner.reset_session() 