from typing import Dict, Any, Optional, Literal, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer

from ..utilities.IdentityManger import get_identity_manager

# State Schema
class AuthState(TypedDict):
    auth_status: Literal["not_authenticated", "authenticated", "registration_needed", "waiting_for_registration", "registration_data_collected", "registration_data_missing", "pii_collection", "waiting_for_pii", "authentication_failed"]
    user_info: Optional[Dict[str, Any]]
    error_message: Optional[str]
    registration_data: Optional[Dict[str, str]]
    pii_data: Optional[Dict[str, str]]
    pii_collection_complete: bool
    auth_result: bool
    notes: Optional[str]

# Input/Output Schemas
class AuthInputState(TypedDict):
    pass  # Empty - no input required

class AuthOutputState(TypedDict):
    auth_result: bool
    notes: Optional[str]
    pii_collection_complete: Optional[bool]

# Checkpointer for auth sessions
auth_checkpointer = SqliteSaver(
    sqlite3.connect("auth_checkpoint.db", check_same_thread=False),
    serde=EncryptedSerializer.from_pycryptodome_aes(),
)

# Global variable for HITL data collection
_pending_user_input = {}

def set_user_input(input_type: str, data: Dict[str, Any]):
    """Set user input from frontend HITL interactions"""
    global _pending_user_input
    _pending_user_input[input_type] = data

def get_user_input(input_type: str) -> Optional[Dict[str, Any]]:
    """Get user input for HITL interactions"""
    global _pending_user_input
    return _pending_user_input.get(input_type)

def clear_user_input():
    """Clear all pending user inputs"""
    global _pending_user_input
    _pending_user_input = {}

# Node Functions
def attempt_login(state: AuthState) -> AuthState:
    """Attempt to login using IdentityManager"""
    try:
        print("Attempting to login...")
        identity_manager = get_identity_manager()
        result = identity_manager.login()

        print(f"Login result: {result}")
        
        if result["result"]:
            return {
                "auth_status": "authenticated",
                "user_info": {
                    "user_id": result["user_id"],
                    "message": result["message"]
                },
                "auth_result": True,
                "notes": result["message"],
                "error_message": None
            }
        else:
            error_msg = result["error"]
            if "Face not recognized" in error_msg:
                return {
                    "auth_status": "registration_needed",
                    "auth_result": False,
                    "notes": "Face not recognized - registration required",
                    "error_message": error_msg
                } # type: ignore
            else:
                return {
                    "auth_status": "authentication_failed",
                    "auth_result": False,
                    "notes": f"Login failed: {error_msg}",
                    "error_message": error_msg
                } # type: ignore
    except Exception as e:
        return {
            "auth_status": "authentication_failed",
            "auth_result": False,
            "notes": f"Authentication error: {str(e)}",
            "error_message": str(e)
        } # type: ignore

def collect_registration_data(state: AuthState) -> AuthState:
    """Collect registration data from frontend (HITL)"""
    # This is a HITL node - data will be set from frontend
    registration_data = get_user_input("registration")
    
    if registration_data:
        return {
            "auth_status": "registration_data_collected",
            "registration_data": registration_data,
            "notes": "Registration data collected successfully"
        } # type: ignore
    else:
        # Wait for user input - frontend will call this again after form submission
        return {
            "auth_status": "waiting_for_registration",
            "notes": "Waiting for registration data from user"
        } # type: ignore

def register_user(state: AuthState) -> AuthState:
    """Register new user using IdentityManager"""
    try:
        registration_data = state.get("registration_data")
        if not registration_data:
            return {
                "auth_status": "registration_data_missing",
                "auth_result": False,
                "notes": "Registration data missing - user needs to choose retry or register",
                "error_message": "Missing registration data"
            }
        
        identity_manager = get_identity_manager()
        result = identity_manager.add_user(
            first_name=registration_data["first_name"],
            last_name=registration_data.get("last_name"),
            dob=registration_data["dob"],
            phone=int(registration_data["phone"])
        )
        
        if result["result"]:
            return {
                "auth_status": "pii_collection",
                "auth_result": False,  # Not fully authenticated yet - need PII
                "user_info": {
                    "user_id": result["user_id"],
                    "message": result["message"]
                },
                "notes": "Registration successful - PII collection required"
            }
        else:
            return {
                "auth_status": "authentication_failed",
                "auth_result": False,
                "notes": f"Registration failed: {result['error']}",
                "error_message": result["error"]
            }
    except Exception as e:
        return {
            "auth_status": "authentication_failed",
            "auth_result": False,
            "notes": f"Registration error: {str(e)}",
            "error_message": str(e)
        }

def collect_pii(state: AuthState) -> AuthState:
    """Collect and encrypt PII data (HITL)"""
    try:
        # Get PII data from frontend HITL
        pii_data = get_user_input("pii")
        
        if not pii_data:
            # Wait for user input - frontend will call this again after form submission
            return {
                "auth_status": "waiting_for_pii",
                "auth_result": False,
                "notes": "Waiting for PII data from user"
            }
        
        identity_manager = get_identity_manager()
        
        # Encrypt and store each PII field
        for data_type, value in pii_data.items():
            if value and value.strip():  # Skip empty values
                result = identity_manager.encrypt_pii_data(data_type, value)
                if not result["result"]:
                    return {
                        "auth_status": "authentication_failed",
                        "auth_result": False,
                        "notes": f"PII encryption failed for {data_type}: {result['error']}",
                        "error_message": result["error"]
                    }
        
        return {
            "auth_status": "authenticated",
            "auth_result": True,
            "pii_collection_complete": True,
            "notes": "Registration and PII collection completed successfully"
        }
        
    except Exception as e:
        return {
            "auth_status": "authentication_failed",
            "auth_result": False,
            "notes": f"PII collection error: {str(e)}",
            "error_message": str(e)
        }

def handle_auth_error(state: AuthState) -> AuthState:
    """Handle authentication errors"""
    error_message = state.get("error_message", "Authentication failed")
    return {
        "auth_result": False,
        "notes": error_message
    }

# Entry point routing function
def route_entry_point(state: AuthState) -> str:
    """Route to appropriate starting node based on initial auth_status"""
    auth_status = state.get("auth_status", "not_authenticated")
    
    if auth_status == "pii_collection":
        return "collect_pii"
    else:
        return "attempt_login"

# Routing Function
def route_auth_result(state: AuthState) -> str:
    """Route based on authentication status"""
    auth_status = state.get("auth_status", "not_authenticated")
    
    if auth_status == "authenticated":
        return "__end__"
    elif auth_status == "registration_needed":
        # Check if we have registration data
        if state.get("registration_data"):
            return "register_user"
        return "collect_registration_data"
    elif auth_status == "waiting_for_registration":
        return "__end__"  # Return to frontend to show registration form
    elif auth_status == "registration_data_collected":
        return "register_user"
    elif auth_status == "registration_data_missing":
        return "__end__"  # Return to frontend to show popup
    elif auth_status == "pii_collection":
        return "__end__"  # Return to frontend to show PII form
    elif auth_status == "waiting_for_pii":
        return "__end__"  # Return to frontend to show PII form (retry)
    elif auth_status == "authentication_failed":
        return "handle_auth_error"
    else:
        return "__end__"

# Graph Builder Function
def create_auth_graph():
    """Create and compile the authentication graph"""
    builder = StateGraph(
        AuthState,
        input_schema=AuthInputState,
        output_schema=AuthOutputState
    )
    
    # Add nodes
    builder.add_node("attempt_login", attempt_login)
    builder.add_node("collect_registration_data", collect_registration_data)
    builder.add_node("register_user", register_user)
    builder.add_node("collect_pii", collect_pii)
    builder.add_node("handle_auth_error", handle_auth_error)
    
    # Add edges - conditional entry point based on initial state
    builder.add_conditional_edges(
        START,
        route_entry_point,
        {
            "attempt_login": "attempt_login",
            "collect_pii": "collect_pii"
        }
    )
    builder.add_conditional_edges(
        "attempt_login",
        route_auth_result,
        {
            "__end__": END,
            "collect_registration_data": "collect_registration_data",
            "register_user": "register_user",
            "authentication_failed": "handle_auth_error"
        }
    )
    
    builder.add_conditional_edges(
        "collect_registration_data",
        route_auth_result,
        {
            "__end__": END,
            "register_user": "register_user"
        }
    )
    
    builder.add_conditional_edges(
        "register_user",
        route_auth_result,
        {
            "__end__": END,
            "collect_registration_data": "collect_registration_data",
            "authentication_failed": "handle_auth_error"
        }
    )
    
    builder.add_conditional_edges(
        "collect_pii",
        route_auth_result,
        {
            "__end__": END,
            "authentication_failed": "handle_auth_error"
        }
    )
    
    builder.add_edge("handle_auth_error", END)
    
    return builder.compile(checkpointer=auth_checkpointer) 