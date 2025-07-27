from typing import Dict, Any, Optional, List, Literal
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode, InjectedState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, trim_messages
from langchain_core.tools import tool
from langchain_ollama.chat_models import ChatOllama
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langchain_community.tools import DuckDuckGoSearchRun
from datetime import datetime, timezone
from langgraph.prebuilt import tools_condition

from ..utilities.IdentityManger import get_identity_manager

# State Schema
class AgentState(TypedDict):
    session_valid: bool
    messages: Annotated[List[BaseMessage], add_messages]
    user_query: Optional[str]
    response: Optional[str]
    pii_cache: Dict[str, str]
    conversation_summary: Optional[str]
    error_message: Optional[str]

# Input/Output Schemas
class AgentInputState(TypedDict):
    user_query: str

class AgentOutputState(TypedDict):
    response: str
    session_valid: bool


reasoning_qwen = ChatOllama(
    model="qwen3:4b",
    temperature=0.1,
    reasoning=True,
    top_p=0.4,
    top_k=10,
    repeat_penalty=1.5,
    base_url="http://localhost:11434/",
)

qwen_fast = ChatOllama(
    model="qwen3:4b",
    temperature=0.1,
    reasoning=False,
    top_p=0.4,
    top_k=10,
    num_predict=1024,
    repeat_penalty=1.5,
    base_url="http://localhost:11434/",
)

# Checkpointer for agent sessions
agent_checkpointer = SqliteSaver(
    sqlite3.connect("agent_checkpoint.db", check_same_thread=False),
    serde=EncryptedSerializer.from_pycryptodome_aes(),
)

# Constants
MAX_MESSAGE_HISTORY = 10

# Tools
@tool
def fetch_user_pii(
    data_keys: List[str],
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Fetch PII data for the authenticated user.
    
    Args:
        data_keys: List of PII keys to fetch (e.g., ["adhaar_number", "pan_number"])
        state: Injected state containing session info
    
    Returns:
        Dict with success status and message
    """
    # Validate session
    if not state.get("session_valid", False):
        return {
            "success": False,
            "error": "User session not valid"
        }
    
    identity_manager = get_identity_manager()
    
    # Verify user is still authenticated
    if not identity_manager.verify_user():
        return {
            "success": False,
            "error": "User not authenticated"
        }
    
    try:
        # Get current cache state
        current_cache = state.get("pii_cache", {})
        retrieved_data = {}
        cache_updates = {}
        missing_keys = []
        
        # Check cache first
        for key in data_keys:
            if key in current_cache:
                retrieved_data[key] = current_cache[key]
                print(f"Retrieved {key} from session cache")
            else:
                missing_keys.append(key)
        
        # Fetch missing keys from secure storage
        if missing_keys:
            # Re-authenticate user before accessing PII
            auth_result = identity_manager.authenticate_user()
            if not auth_result:
                return {
                    "success": False,
                    "error": "User re-authentication failed"
                }
            
            # Fetch the missing PII data
            for key in missing_keys:
                result = identity_manager.decrypt_pii_data(key)
                if result.get("result"):
                    retrieved_data[key] = result["data"]
                    cache_updates[key] = result["data"]  # Cache the decrypted data
                    print(f"Retrieved and cached {key} from secure storage")
                else:
                    return {
                        "success": False,
                        "error": f"Failed to retrieve {key}: {result.get('error', 'Unknown error')}"
                    }
        
        print("PII data retrieved successfully")
        print(retrieved_data)  # Display to user (not returned to LLM)
        
        # Update state with new cache entries
        state["pii_cache"].update(cache_updates)
        
        return {
            "success": True,
            "message": "PII data retrieved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"PII retrieval failed: {str(e)}"
        }

@tool
def government_scheme_lookup(query: str) -> Dict[str, Any]:
    """
    Search the web for latest Indian government schemes and benefits.
    
    Args:
        query: Search query for government schemes (e.g., "housing schemes for low income", "farmer subsidies 2024")
    
    Returns:
        Dict with search results containing scheme information
    """
    try:
        # Initialize DuckDuckGo search
        search = DuckDuckGoSearchRun()
        
        # Enhance query with Indian government context
        enhanced_query = f"India government scheme {query} official latest 2024"
        
        # Perform the search
        search_results = search.run(enhanced_query)
        
        if search_results:
            return {
                "success": True,
                "results": search_results,
                "query": query,
                "note": "These are web search results. Please verify information from official government sources."
            }
        else:
            return {
                "success": False,
                "message": "No results found. Try refining your search query.",
                "query": query
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "query": query
        }

@tool
def get_current_datetime() -> Dict[str, str]:
    """
    Get the current date and time in UTC format.
    
    Returns:
        Dict containing current UTC datetime in various formats
    """
    try:
        now_utc = datetime.now(timezone.utc)
        
        return {
            "success": True,
            "iso_format": now_utc.isoformat(),
            "readable_format": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "date": now_utc.strftime("%Y-%m-%d"),
            "time": now_utc.strftime("%H:%M:%S"),
            "day_of_week": now_utc.strftime("%A"),
            "timestamp": int(now_utc.timestamp())
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get datetime: {str(e)}"
        }

# Node Functions
def validate_session(state: AgentState) -> AgentState:
    """Validate that the user session is still active"""
    identity_manager = get_identity_manager()
    
    if identity_manager.verify_user():
        return {
            "session_valid": True
        }
    else:
        return {
            "session_valid": False,
            "error_message": "Session expired. Please re-authenticate.",
            "response": "Your session has expired. Please authenticate again to continue."
        }

def process_query(state: AgentState) -> AgentState:
    """Process the user query and prepare for LLM"""
    user_query = state.get("user_query", "")
    
    if not user_query:
        return {
            "response": "I didn't receive your query. Please try again.",
            "error_message": "No query provided"
        }
    
    # Add system message if it's the first message
    messages = state.get("messages", [])
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        system_msg = SystemMessage(content="""You are Saarthi, an intelligent government scheme assistant for Indian citizens. 
You help users discover and apply for government schemes. You have access to:
1. fetch_user_pii - to retrieve user's stored documents like Aadhaar, PAN, etc.
2. government_scheme_lookup - to search for relevant government schemes

Call the tools when the user asks a query regarding their PII, government schemes, benefits or any related information.
The tools can be called by returning a tool_calls object in your response.
Be helpful, clear, and concise. When users ask about schemes, provide specific information about eligibility, required documents, and application process.
Always communicate in simple, easy-to-understand language.""")
        messages = [system_msg] + messages
    
    # Add user message
    messages.append(HumanMessage(content=user_query))
    
    return {
        "messages": messages
    }

def summarize_conversation(state: AgentState) -> AgentState:
    """Summarize old messages to save space"""
    messages = state.get("messages", [])
    
    if len(messages) <= MAX_MESSAGE_HISTORY:
        return state
    
    # Get messages to summarize (keep system message and summarize the rest)
    system_msg = next((msg for msg in messages if isinstance(msg, SystemMessage)), None)
    messages_to_summarize = messages[1:MAX_MESSAGE_HISTORY] if system_msg else messages[:MAX_MESSAGE_HISTORY]
    
    # Create summary prompt
    summary_prompt = SystemMessage(content="Summarize the following conversation between the user and assistant in bullet points, keeping key information about schemes discussed, user queries, and any important decisions:")
    
    # Use fast LLM for summarization
    summary_response = qwen_fast.invoke([summary_prompt] + messages_to_summarize)
    
    # Update conversation summary
    old_summary = state.get("conversation_summary", "")
    if old_summary:
        new_summary = f"{old_summary}\n\n{summary_response.content}"
    else:
        new_summary = summary_response.content
    
    # Keep only recent messages
    recent_messages = [system_msg] if system_msg else []
    recent_messages.extend(messages[-MAX_MESSAGE_HISTORY:])
    
    return {
        "conversation_summary": new_summary,
        "messages": recent_messages
    }

def llm_interaction(state: AgentState) -> AgentState:
    """Handle LLM interaction with tools"""
    messages = state.get("messages", [])
    conversation_summary = state.get("conversation_summary", "")
    
    # Prepare context with summary if exists
    context_messages = []
    if conversation_summary:
        context_messages.append(SystemMessage(content=f"Previous conversation summary:\n{conversation_summary}"))
    context_messages.extend(messages)
    
    # Bind tools to LLM
    llm_with_tools = reasoning_qwen.bind_tools([fetch_user_pii, government_scheme_lookup, get_current_datetime])
    
    try:
        # Get LLM response
        response = llm_with_tools.invoke(context_messages)
        
        # Check if it's a valid response

        #Debug prints
        print(f"LLM Response: {response}")

        if response.content:
            print(f"Assistant: {response.content}")
            return {
                "messages": [response],
                "response": response.content
            }
        else:
            # Handle tool calls in the tool node
            return {
                "messages": [response]
            }
    except Exception as e:
        error_msg = f"I encountered an error processing your request: {str(e)}"
        return {
            "response": error_msg,
            "error_message": str(e),
            "messages": [AIMessage(content=error_msg)]
        }

def handle_error(state: AgentState) -> AgentState:
    """Handle errors gracefully"""
    error_message = state.get("error_message", "An unexpected error occurred")
    return {
        "response": f"I apologize, but {error_message}. Please try again or contact support if the issue persists.",
        "session_valid": False
    }

# Routing Functions
def route_session(state: AgentState) -> str:
    """Route based on session validity"""
    if state.get("session_valid", False):
        return "process_query"
    else:
        return "handle_error"

def route_summarize(state: AgentState) -> str:
    """Check if conversation needs summarization"""
    messages = state.get("messages", [])
    if len(messages) > MAX_MESSAGE_HISTORY:
        return "summarize_conversation"
    return "llm_interaction"

# Graph Builder Function
def create_agent_graph():
    """Create and compile the agent graph"""
    builder = StateGraph(
        AgentState,
        input_schema=AgentInputState,
        output_schema=AgentOutputState
    )
    
    # Add nodes
    builder.add_node("validate_session", validate_session)
    builder.add_node("is_session_valid", lambda state: state)
    builder.add_node("process_query", process_query)
    builder.add_node("should_summarize", lambda state: state)
    builder.add_node("summarize_conversation", summarize_conversation)
    builder.add_node("llm_interaction", llm_interaction)
    builder.add_node("tools", ToolNode([fetch_user_pii, government_scheme_lookup, get_current_datetime]))
    builder.add_node("handle_error", handle_error)
    
    # Add edges
    builder.add_edge(START, "validate_session")
    builder.add_edge("validate_session", "is_session_valid")
    builder.add_conditional_edges(
        "is_session_valid", 
        route_session,
        {
            "process_query": "process_query",
            "handle_error": "handle_error"
        })
    builder.add_edge("process_query", "should_summarize")
    builder.add_conditional_edges(
        "should_summarize", 
        route_summarize,
        {
            "llm_interaction": "llm_interaction",
            "summarize_conversation": "summarize_conversation"
        })
    builder.add_edge("summarize_conversation", "llm_interaction")
    builder.add_conditional_edges("llm_interaction", tools_condition)
    builder.add_edge("tools", "llm_interaction")
    builder.add_edge("handle_error", END)
    
    return builder.compile(checkpointer=agent_checkpointer) 