from typing import Dict, Any, Optional
import uuid
from .auth_graph import create_auth_graph, set_user_input, clear_user_input
from .agent_graph import create_agent_graph

class AuthGraphRunner:
    """Simple interface for running the authentication graph from frontend"""
    
    def __init__(self):
        self.auth_graph = create_auth_graph()
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

class AgentGraphRunner:
    """Simple interface for running the agent graph from frontend"""
    
    def __init__(self):
        self.agent_graph = create_agent_graph()
        self.current_thread_id = None
    
    def start_conversation(self, user_id: str) -> str:
        """Start a new conversation session for a user"""
        # Generate thread ID for this conversation
        self.current_thread_id = f"agent_{user_id}_{uuid.uuid4()}"
        return self.current_thread_id
    
    def send_message(self, user_query: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a message to the agent and get response"""
        # Use provided thread_id or current one
        thread_to_use = thread_id or self.current_thread_id
        
        if not thread_to_use:
            return {
                "success": False,
                "response": "No active conversation session",
                "session_valid": False
            }
        
        try:
            # Run the agent graph
            result = self.agent_graph.invoke(
                {"user_query": user_query},
                config={"configurable": {"thread_id": thread_to_use}}
            )
            
            return {
                "success": True,
                "response": result.get("response", ""),
                "session_valid": result.get("session_valid", True)
            }
        except Exception as e:
            return {
                "success": False,
                "response": f"Error processing your request: {str(e)}",
                "session_valid": False,
                "error": str(e)
            }
    
    def end_conversation(self):
        """End the current conversation session"""
        self.current_thread_id = None

# Global instances for frontend use
auth_runner = AuthGraphRunner()
agent_runner = AgentGraphRunner()

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

def start_agent_conversation(user_id: str) -> str:
    """Start a new agent conversation - used by frontend"""
    return agent_runner.start_conversation(user_id)

def send_agent_message(user_query: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """Send message to agent - used by frontend"""
    return agent_runner.send_message(user_query, thread_id)

def end_agent_conversation():
    """End agent conversation - used by frontend"""
    agent_runner.end_conversation() 