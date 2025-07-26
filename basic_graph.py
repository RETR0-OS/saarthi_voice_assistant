from saarthi_assistant.identity_wallet.identity_manager.identity_manager import IdentityManager
from langgraph.graph import START, END, StateGraph, add_messages
from langgraph.graph.message import MessagesState
from typing_extensions import TypedDict
from typing import Annotated, Any, Dict, List, Optional, Union, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_ollama.chat_models import ChatOllama
from langgraph.prebuilt import InjectedState, ToolNode, tools_condition
from langchain_core.tools import tool
from dataclasses import dataclass
from enum import Enum
from langchain_core.messages.utils import (
    trim_messages,
    count_tokens_approximately
)
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from dotenv import load_dotenv

load_dotenv()

# LLM definitions
reasoning_qwen = ChatOllama(
    model="qwen3:4b",
    temperature=0.1,
    reasoning=True,
    top_p=0.4,
    top_k=10,
    repeat_penalty=1.5
)

qwen_fast = ChatOllama(
    model="qwen3:4b",
    temperature=0.1,
    reasoning=False,
    top_p=0.4,
    top_k=10,
    num_predict=1024,
    repeat_penalty=1.5
)

# Setup Checkopoint store for short-term memory
checkpointer = SqliteSaver(
    sqlite3.connect("checkpoint.db", check_same_thread=False),
    serde=EncryptedSerializer.from_pycryptodome_aes(),
)

MAX_MESSAGE_HISTORY = 10


# Enums for state management
class AuthenticationStatus(Enum):
    NOT_AUTHENTICATED = "not_authenticated"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    AUTHENTICATION_FAILED = "authentication_failed"
    REGISTRATION_REQUIRED = "registration_required"


class WorkflowPhase(Enum):
    INITIALIZATION = "initialization"
    AUTHENTICATION = "authentication"
    REGISTRATION = "registration"
    PII_SETUP = "pii_setup"
    QUERY_PROCESSING = "query_processing"
    COMPLETED = "completed"


# Runtime Context for dependency injection
@dataclass
class RuntimeContext:
    identity_manager: IdentityManager
    camera_id: int = 1
    max_auth_attempts: int = 3
    available_pii_keys: Optional[List[str]] = None

    def __post_init__(self):
        if self.available_pii_keys is None:
            self.available_pii_keys = ["adhaar_number", "pan_number"]


# Reducer functions
def merge_user_data(left: Optional[Dict], right: Optional[Dict]) -> Optional[Dict]:
    """Merge user data dictionaries"""
    if right is None:
        return left
    if left is None:
        return right
    return {**left, **right}


def collect_errors(left: List[str], right: List[str]) -> List[str]:
    """Collect errors without duplicates"""
    if not right:
        return left
    return left + [error for error in right if error not in left]


def merge_pii_cache(left: Optional[Dict[str, str]], right: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Merge PII cache dictionaries"""
    if left is None:
        left = {}
    if right is None:
        right = {}
    return {**left, **right}


# State Schemas
class SaarthiInputState(TypedDict):
    first_name: Optional[str]
    last_name: Optional[str]
    dob: Optional[str]
    phone: Optional[int]
    query: Optional[str]


class SaarthiOutputState(TypedDict):
    message: str
    status: str
    user_authenticated: bool


# Main unified state schema
class SaarthiState(TypedDict):
    # Core workflow state
    current_phase: WorkflowPhase
    auth_status: AuthenticationStatus

    # Message handling
    conversation_summary: Optional[str]
    messages: Annotated[List[BaseMessage], add_messages]

    # User data with proper reducers
    user_registration_data: Annotated[Optional[Dict[str, Any]], merge_user_data]
    current_user_info: Annotated[Optional[Dict[str, Any]], merge_user_data]

    # Error handling
    errors: Annotated[List[str], collect_errors]
    auth_attempts: int

    # PII management
    available_pii_keys: List[str]

    # Identity manager session info (not the instance itself)
    session_info: Optional[Dict[str, Any]]

    llm_input_messages: Annotated[List[BaseMessage], add_messages]

    # Private PII cache for thread-specific short-term memory (not exposed to LLM/user)
    private_pii_cache: Annotated[Dict[str, str], merge_pii_cache]


# Dependency injection using closure pattern
_IDENTITY_MANAGER: Optional[IdentityManager] = None
_RUNTIME_CONTEXT: Optional[RuntimeContext] = None


def set_runtime_context(identity_manager: IdentityManager, camera_id: int = 0):
    """Set the runtime context for dependency injection"""
    global _IDENTITY_MANAGER, _RUNTIME_CONTEXT
    _IDENTITY_MANAGER = identity_manager
    _RUNTIME_CONTEXT = RuntimeContext(
        identity_manager=identity_manager,
        camera_id=camera_id
    )


# Nodes with proper state management

## Router Nodes
def route_from_initialization(state: SaarthiState) -> str:
    """Route from initialization based on available data"""
    if state.get("user_registration_data"):
        return "new_registration"
    return "authenticate"


def route_based_on_auth_status(state: SaarthiState) -> str:
    """Route based on authentication status and state"""
    auth_status = state.get("auth_status", AuthenticationStatus.NOT_AUTHENTICATED)
    auth_attempts = state.get("auth_attempts", 0)
    max_attempts = 3

    if auth_status == AuthenticationStatus.AUTHENTICATED:
        return "query_handler"
    elif auth_status == AuthenticationStatus.REGISTRATION_REQUIRED:
        return "registration_flow"
    elif auth_status == AuthenticationStatus.AUTHENTICATION_FAILED:
        if auth_attempts >= max_attempts:
            return "error_handler"
        else:
            return "retry_authentication"
    else:
        return "authenticate_user"


def decide_summarize(state: SaarthiState) -> str:
    """
    Decide whether to trim message history and create update summary to save space
    """
    if len(state["messages"]) >= MAX_MESSAGE_HISTORY:
        return "summarize_messages"
    else:
        return "continue"


def decide_end(state: SaarthiState) -> str:
    if len(state["messages"]) > 0:
        return "continue"
    last_human_message = None
    for msg in state["messages"][::-1]:
        if isinstance(msg, HumanMessage):
            last_human_message = msg
            break

    if last_human_message is None:
        return "continue"

    system = SystemMessage(
        content="Determine whether the user the wants to terminate the conversation" \
                "If the message indicates that the user wants to end the conversation, " \
                "output 'end' else output 'continue'. DO NOT OUTPUT ANY OTHER WORD, EXPLANATION" \
                "CONTENT OR FORMATTING. Your only output should be 'end' or 'continue'"
    )

    response = qwen_fast.invoke(
        [system, last_human_message]
    )

    return str(response.content).lower()


## Processing Nodes
def initialize_workflow(state: SaarthiState) -> Dict[str, Any]:
    """Initialize the workflow with proper state structure"""
    # Extract input data if present
    user_data = {}
    for key in ["first_name", "last_name", "dob", "phone"]:
        if key in state and state[key] is not None:
            user_data[key] = state[key]

    # Initialize PII cache - will be empty for new threads or retained for existing threads
    pii_cache = state.get("private_pii_cache", {})

    return {
        "current_phase": WorkflowPhase.INITIALIZATION,
        "auth_status": AuthenticationStatus.NOT_AUTHENTICATED,
        "messages": state.get("messages", []),
        "user_registration_data": user_data if user_data else None,
        "current_user_info": None,
        "errors": [],
        "auth_attempts": 0,
        "available_pii_keys": _RUNTIME_CONTEXT.available_pii_keys if _RUNTIME_CONTEXT else ["adhaar_number",
                                                                                            "pan_number"],
        "session_info": None,
        "private_pii_cache": pii_cache
    }


def authenticate_user(state: SaarthiState) -> Dict[str, Any]:
    """Authenticate user with proper state updates"""
    if not _IDENTITY_MANAGER:
        return {
            "errors": ["Identity manager not initialized"],
            "auth_status": AuthenticationStatus.AUTHENTICATION_FAILED
        }

    # Update phase
    updates = {
        "current_phase": WorkflowPhase.AUTHENTICATION,
        "auth_status": AuthenticationStatus.AUTHENTICATING,
        "auth_attempts": state.get("auth_attempts", 0) + 1
    }

    try:
        result = _IDENTITY_MANAGER.login()

        if result["result"]:
            updates.update({
                "auth_status": AuthenticationStatus.AUTHENTICATED,
                "current_user_info": {
                    "user_id": result["user_id"],
                    "message": result["message"]
                },
                "session_info": {
                    "logged_in": True,
                    "session_active": _IDENTITY_MANAGER.verify_user()
                },
                "errors": []  # Clear previous errors on success
            })
        else:
            error_msg = result["error"]
            if "Face not recognized" in error_msg:
                updates.update({
                    "auth_status": AuthenticationStatus.REGISTRATION_REQUIRED,
                    "errors": [error_msg]
                })
            else:
                updates.update({
                    "auth_status": AuthenticationStatus.AUTHENTICATION_FAILED,
                    "errors": [error_msg]
                })

    except Exception as e:
        updates.update({
            "auth_status": AuthenticationStatus.AUTHENTICATION_FAILED,
            "errors": [f"Authentication error: {str(e)}"]
        })

    return updates


def get_user_query(state: SaarthiState) -> Dict[str, Any]:
    """Get user query and prepare for LLM processing"""
    system_message = SystemMessage(
        content="You are a helpful assistant that communicates in ENGLISH ONLY. Please answer the user's query. "
                "If the user asks for their personal information, use the fetch_user_pii tool to retrieve it. "
                "You will not have access to the user's personal information. "
                "As soon as you call the fetch_user_pii tool, the user will receive their information automatically. "
                "You will only know the status of the tool call, not the actual data. "
                "If the authentication fails, do not retry the tool call. "
                "Notify the user that the authentication failed and they need to login again. Do not call tools if authentication fails. "
                "Fetch all the PII data from the IdentityManager. " \
                "COMMUNICATE AND THINK IN ENGLISH ONLY. DO NOT USE ANY OTHER LANGUAGE" \
                "You have access to the following keys for the PII: " + str(state.get("available_pii_keys", []))
    )

    query = input("Enter your query: ")

    return {
        "messages": [system_message, HumanMessage(content=query)],
        "current_phase": WorkflowPhase.QUERY_PROCESSING
    }


def get_registration_info(state: SaarthiState) -> Dict[str, Any]:
    """Get registration information from user"""
    first_name = input("Enter your first name: ")
    last_name = input("Enter your last name: ")
    dob = input("Enter your date of birth (YYYY-MM-DD): ")
    phone = int(input("Enter your phone number: "))

    return {
        "user_registration_data": {
            "first_name": first_name,
            "last_name": last_name,
            "dob": dob,
            "phone": phone
        },
        "current_phase": WorkflowPhase.REGISTRATION
    }


def register_new_user(state: SaarthiState) -> Dict[str, Any]:
    """Register new user with proper error handling"""
    if not _IDENTITY_MANAGER:
        return {
            "errors": ["Identity manager not initialized"],
            "auth_status": AuthenticationStatus.AUTHENTICATION_FAILED
        }

    registration_data = state.get("user_registration_data")

    if not registration_data:
        return {
            "errors": ["No registration data available"],
            "auth_status": AuthenticationStatus.AUTHENTICATION_FAILED
        }

    try:
        result = _IDENTITY_MANAGER.add_user(**registration_data)
        if result["result"]:
            return {
                "current_user_info": {
                    "user_id": result["user_id"],
                    "message": result["message"]
                },
                "auth_status": AuthenticationStatus.AUTHENTICATED,
                "current_phase": WorkflowPhase.PII_SETUP,
                "errors": []
            }
        else:
            return {
                "errors": [result["error"]],
                "auth_status": AuthenticationStatus.AUTHENTICATION_FAILED
            }
    except Exception as e:
        return {
            "errors": [f"Registration failed: {str(e)}"],
            "auth_status": AuthenticationStatus.AUTHENTICATION_FAILED
        }


def setup_user_pii(state: SaarthiState) -> Dict[str, Any]:
    """Setup PII data for the user"""
    if not _IDENTITY_MANAGER:
        return {
            "errors": ["Identity manager not initialized"]
        }

    try:
        adhaar_number = input("Enter your Aadhaar number: ")
        result1 = _IDENTITY_MANAGER.encrypt_pii_data("adhaar_number", adhaar_number)

        pan_number = input("Enter your PAN number: ")
        result2 = _IDENTITY_MANAGER.encrypt_pii_data("pan_number", pan_number)

        errors = []
        if not result1.get("result"):
            errors.append(f"Aadhaar encryption failed: {result1.get('error', 'Unknown error')}")
        if not result2.get("result"):
            errors.append(f"PAN encryption failed: {result2.get('error', 'Unknown error')}")

        if errors:
            return {"errors": errors}

        return {
            "current_phase": WorkflowPhase.COMPLETED,
            "session_info": {
                "pii_setup_complete": True,
                "logged_in": True,
                "session_active": _IDENTITY_MANAGER.verify_user()
            }
        }
    except Exception as e:
        return {
            "errors": [f"PII setup failed: {str(e)}"]
        }


def logout_user(state: SaarthiState) -> Dict[str, Any]:
    """Process user logout and clear session data including PII cache"""
    return {
        "current_phase": WorkflowPhase.AUTHENTICATION,
        "auth_status": AuthenticationStatus.NOT_AUTHENTICATED,
        "current_user_info": None,
        "session_info": None,
        "private_pii_cache": {},  # Clear the PII cache on logout
        "messages": state.get("messages", []) + [SystemMessage(content="User logged out successfully")]
    }


def handle_llm_interaction(state: SaarthiState) -> Dict[str, Any]:
    """Handle LLM interactions with tools"""
    llm_with_tools = reasoning_qwen.bind_tools([fetch_user_pii, fill_secure_form])

    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        max_tokens=4096,
        token_counter=count_tokens_approximately,
        start_on="system",
        end_on=("human", "tool")
    )

    response = llm_with_tools.invoke(trimmed_messages)

    print("LLM response:", response)

    if response.content:
        print(response.pretty_print())

    return {
        "messages": [response]
    }


def handle_workflow_errors(state: SaarthiState) -> Dict[str, Any]:
    """Centralized error handling with recovery options"""
    errors = state.get("errors", [])
    auth_attempts = state.get("auth_attempts", 0)
    max_attempts = 3

    if not errors:
        return {"current_phase": WorkflowPhase.COMPLETED}

    latest_error = errors[-1]

    if "authentication" in latest_error.lower() and auth_attempts < max_attempts:
        return {
            "current_phase": WorkflowPhase.AUTHENTICATION,
            "auth_status": AuthenticationStatus.NOT_AUTHENTICATED,
            "errors": []  # Clear errors for retry
        }

    return {
        "current_phase": WorkflowPhase.COMPLETED,
        "messages": [SystemMessage(content=f"Workflow failed: {latest_error}")]
    }


def summarize_conversation(state: SaarthiState) -> SaarthiState:
    """
    Summarize the conversation to save space in message history.
    """
    if not state["messages"] or len(state["messages"]) < MAX_MESSAGE_HISTORY:
        return {
            "conversation_summary": None
        }

    # Choose Messages to summarize and delete
    messages_to_summarize = trim_messages(
        state["messages"],
        strategy="first",
        max_tokens=4096,
        token_counter=count_tokens_approximately,
        end_on=("ai", "human")
    )

    old_summary = state.get("conversation_summary", "")

    messages_to_summarize.append(SystemMessage(content=f"Old conversation summary is: {old_summary}"))

    instruction = SystemMessage(
        content="Summarize the below conversation between the user and the assistant" \
                "in the form of bullet points while retaining any critical information." \
                "Make sure to track any topics discussed, conclusions reached, steps completes." \
                "and any follow-up actions required. " \
                "The summary should be concise and focused on the key points of the conversation."
    )

    messages_to_summarize.insert(0, instruction)

    # Use LLM to summarize the conversation
    summary_response = qwen_fast.invoke(messages_to_summarize)

    # Delete the summarized messages from the state
    updated_messages = state["messages"][-MAX_MESSAGE_HISTORY:]

    if summary_response.content:
        return {
            "conversation_summary": summary_response.content,
            "messages": updated_messages
        }
    return {"conversation_summary": None}


# Tools with enhanced state management
@tool
def fetch_user_pii(
        data_keys: List[str],
        state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Fetch PII data with state validation and session caching.
    First checks the session cache, then fetches from secure storage if needed.

    Args:
        data_keys (List[str]): List of keys for the PII data to be fetched.
        state (SaarthiState): The state of the graph.

    Returns:
        dict[str, Any]: A dictionary containing the status of the tool call and cache updates.
    """
    # Validate authentication status
    auth_status = state.get("auth_status")
    if auth_status != AuthenticationStatus.AUTHENTICATED:
        return {
            "success": False,
            "error": "User not authenticated",
            "required_action": "authenticate",
            "private_pii_cache": {}
        }

    # Validate session
    session_info = state.get("session_info")
    if not session_info or not session_info.get("session_active"):
        return {
            "success": False,
            "error": "Session not active",
            "required_action": "re_authenticate",
            "private_pii_cache": {}
        }

    print("Accessing PII data for user...")

    if not _IDENTITY_MANAGER:
        return {
            "success": False,
            "error": "Identity manager not available",
            "private_pii_cache": {}
        }

    try:
        # Get current cache state
        current_cache = state.get("private_pii_cache", {})
        retrieved_data = {}
        cache_updates = {}
        missing_keys = []

        # Check cache first for each requested key
        for key in data_keys:
            if key in current_cache:
                retrieved_data[key] = current_cache[key]
                print(f"Retrieved {key} from session cache")
            else:
                missing_keys.append(key)

        # Fetch missing keys from secure storage
        if missing_keys:
            # Authenticate user before accessing PII
            auth_result = _IDENTITY_MANAGER.authenticate_user()
            if not auth_result:
                return {
                    "success": False,
                    "error": "User re-authentication failed",
                    "private_pii_cache": {}
                }

            # Fetch the missing PII data
            for key in missing_keys:
                result = _IDENTITY_MANAGER.decrypt_pii_data(key)
                if result.get("result"):
                    retrieved_data[key] = result["data"]
                    cache_updates[key] = result["data"]  # Cache the decrypted data
                    print(f"Retrieved and cached {key} from secure storage")
                else:
                    return {
                        "success": False,
                        "error": f"Failed to retrieve {key}: {result.get('error', 'Unknown error')}",
                        "private_pii_cache": {}
                    }

        print("PII data retrieved successfully")
        print(retrieved_data)  # Display to user (not returned to LLM)

        return {
            "success": True,
            "message": "PII data retrieved successfully",
            "private_pii_cache": cache_updates  # Only return new cache entries
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"PII retrieval failed: {str(e)}",
            "private_pii_cache": {}
        }


@tool
def fill_secure_form(
        regular_form_ids: Dict[str, Any],
        pii_form_ids: List[str],
        pii_data_keys: List[str],
        state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Fill form with user's PII data securely using session cache when available.

    Args:
        regular_form_ids: Regular form field IDs that can be filled by the LLM.
        pii_form_ids: Form field IDs that require PII to fill.
        pii_data_keys: Keys for the PII data to be filled.
        state: The state of the graph.

    Returns:
        dict[str, Any]: A dictionary containing the status of the tool call and cache updates.
    """
    # Validate authentication status
    auth_status = state.get("auth_status")
    if auth_status != AuthenticationStatus.AUTHENTICATED:
        return {
            "success": False,
            "error": "User not authenticated",
            "required_action": "authenticate",
            "private_pii_cache": {}
        }

    # Validate session
    session_info = state.get("session_info")
    if not session_info or not session_info.get("session_active"):
        return {
            "success": False,
            "error": "Session not active",
            "required_action": "re_authenticate",
            "private_pii_cache": {}
        }

    print("Filling form with PII data...")

    if not _IDENTITY_MANAGER:
        return {
            "success": False,
            "error": "Identity manager not available",
            "private_pii_cache": {}
        }

    try:
        # Get current cache state
        current_cache = state.get("private_pii_cache", {})
        pii_data = {}
        cache_updates = {}
        missing_keys = []

        # Check cache first for each required PII key
        for key in pii_data_keys:
            if key in current_cache:
                pii_data[key] = current_cache[key]
                print(f"Using cached {key} for form filling")
            else:
                missing_keys.append(key)

        # Fetch missing keys from secure storage
        if missing_keys:
            # Authenticate user before accessing PII
            auth_result = _IDENTITY_MANAGER.authenticate_user()
            if not auth_result:
                return {
                    "success": False,
                    "error": "User re-authentication failed",
                    "private_pii_cache": {}
                }

            # Fetch the missing PII data
            for key in missing_keys:
                result = _IDENTITY_MANAGER.decrypt_pii_data(key)
                if result.get("result"):
                    pii_data[key] = result["data"]
                    cache_updates[key] = result["data"]  # Cache the decrypted data
                    print(f"Retrieved and cached {key} for form filling")
                else:
                    return {
                        "success": False,
                        "error": f"Failed to retrieve {key} for form filling",
                        "private_pii_cache": {}
                    }

        print("Form filled successfully with secure PII data")

        return {
            "success": True,
            "message": "Form filled successfully",
            "private_pii_cache": cache_updates  # Only return new cache entries
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Form filling failed: {str(e)}",
            "private_pii_cache": {}
        }


# Graph factory function
def create_saarthi_graph(identity_manager: IdentityManager, camera_id: int = 0):
    """Create the refactored Saarthi graph with dependency injection"""

    # Set up the runtime context
    set_runtime_context(identity_manager, camera_id)

    builder = StateGraph(
        SaarthiState,
        input_schema=SaarthiInputState,
        output_schema=SaarthiOutputState
    )

    # Add nodes with clear responsibilities
    builder.add_node("initialize", initialize_workflow)
    builder.add_node("authenticate", authenticate_user)
    builder.add_node("register_user", register_new_user)
    builder.add_node("setup_pii", setup_user_pii)
    builder.add_node("query_handler", handle_llm_interaction)
    builder.add_node("get_query", get_user_query)
    builder.add_node("get_registration_info", get_registration_info)
    builder.add_node("error_handler", handle_workflow_errors)
    builder.add_node("should_summarize", lambda state: state)
    builder.add_node("summarize_conversation", summarize_conversation)
    builder.add_node("decide_conversation_end", lambda state: state)

    # Add tools
    builder.add_node("tools", ToolNode([fetch_user_pii, fill_secure_form]))

    # Define clear routing
    builder.add_edge(START, "initialize")
    builder.add_conditional_edges(
        "initialize",
        route_from_initialization,
        {
            "new_registration": "get_registration_info",
            "authenticate": "authenticate"
        }
    )

    builder.add_conditional_edges(
        "authenticate",
        route_based_on_auth_status,
        {
            "query_handler": "get_query",
            "registration_flow": "get_registration_info",
            "retry_authentication": "authenticate",
            "error_handler": "error_handler"
        }
    )

    builder.add_edge("get_query", "should_summarize")

    builder.add_conditional_edges(
        "should_summarize",
        decide_summarize,
        {
            "summarize_messages": "summarize_conversation",
            "continue": "query_handler"
        }
    )

    builder.add_edge("summarize_conversation", "query_handler")
    builder.add_edge("get_registration_info", "register_user")
    builder.add_edge("register_user", "setup_pii")
    builder.add_edge("setup_pii", "get_query")
    builder.add_conditional_edges("query_handler", tools_condition, {
        "tools": "tools",
        "__end__": "decide_conversation_end"
    })

    builder.add_conditional_edges(
        "decide_conversation_end",
        decide_end,
        {
            "continue": "get_query",
            "end": END
        }
    )

    builder.add_edge("tools", "query_handler")
    builder.add_edge("error_handler", END)

    return builder.compile(checkpointer=checkpointer)


# Main execution
if __name__ == "__main__":
    # Create identity manager instance (replacing singleton pattern)
    identity_manager = IdentityManager(camera_id=1)

    # Create and run the graph
    graph = create_saarthi_graph(identity_manager)
    print(graph.get_graph().draw_mermaid())

    # Run with sample input
    result = graph.invoke({
        "first_name": "Aaditya",
        "last_name": "Jindal",
        "dob": "2000-01-01",
        "phone": 1234567890,
        "query": None
    },
        {"configurable": {"thread_id": "1"}},
    )

    # print("Graph execution completed:", result)