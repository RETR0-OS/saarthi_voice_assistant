from typing import Dict, Any, Optional, List
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode, InjectedState, tools_condition
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
from langchain_ollama.chat_models import ChatOllama

from ..identity_wallet.identity_manager.identity_manager import IdentityManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse

from ..utilities.IdentityManger import get_identity_manager

# State Schema
class FormFillerState(TypedDict):
    form_url: str
    messages: Annotated[List[BaseMessage], add_messages]
    html_content: Optional[str]
    form_fields: Optional[Dict[str, Any]]
    user_pii_data: Optional[Dict[str, str]]
    form_submission_result: Optional[Dict[str, Any]]
    browser_session: Optional[Any]
    final_report: Optional[str]
    error_message: Optional[str]

# Input/Output Schemas
class FormFillerInputState(TypedDict):
    identity_manager: IdentityManager
    form_url: str

class FormFillerOutputState(TypedDict):
    success: bool
    final_report: str
    submission_result: Optional[Dict[str, Any]]

# LLM Configuration - Non-reasoning qwen3:4b for ReAct orchestration
form_filler_llm = ChatOllama(
    model="qwen3:4b",
    temperature=0.1,
    reasoning=False,
    top_p=0.4,
    top_k=10,
    num_predict=1024,
    repeat_penalty=1.5,
    base_url="http://localhost:11434/",
)



def get_selenium_driver():
    """Get a configured Selenium Chrome driver"""
    chrome_options = Options()
    # Remove headless mode so user can see the form being filled
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"Failed to initialize Chrome driver: {e}")
        return None

# Tools
@tool
def get_form(
    form_url: str,
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Fetch HTML content of the form page using Selenium.
    
    Args:
        form_url: URL of the form to fetch
        state: Injected state for browser session management
    
    Returns:
        Dict with success status and HTML content
    """
    try:
        # Initialize browser if not exists
        if not state.get("browser_session"):
            driver = get_selenium_driver()
            if not driver:
                return {
                    "success": False,
                    "error": "Failed to initialize browser driver"
                }
            state["browser_session"] = driver
        else:
            driver = state["browser_session"]
        
        # Navigate to the form URL
        print(f"Navigating to: {form_url}")
        driver.get(form_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Get page source
        html_content = driver.page_source
        
        # Store in state
        state["html_content"] = html_content
        
        return {
            "success": True,
            "message": f"Successfully fetched HTML content from {form_url}",
            "content_length": len(html_content)
        }
        
    except TimeoutException:
        return {
            "success": False,
            "error": f"Timeout while loading {form_url}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch form: {str(e)}"
        }

@tool
def parse_form(
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Parse HTML content to extract form fields and their requirements.
    
    Args:
        state: Injected state containing HTML content
    
    Returns:
        Dict with form fields structure and requirements
    """
    try:
        html_content = state.get("html_content")
        if not html_content:
            return {
                "success": False,
                "error": "No HTML content available. Please fetch the form first."
            }
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all forms on the page
        forms = soup.find_all('form')
        if not forms:
            return {
                "success": False,
                "error": "No forms found on the page"
            }
        
        # Parse the first form (or most likely form)
        form = forms[0]
        form_fields = {}
        
        # Extract input fields
        inputs = form.find_all(['input', 'select', 'textarea'])
        
        for field in inputs:
            field_name = field.get('name') or field.get('id')
            if not field_name:
                continue
                
            field_type = field.get('type', 'text')
            field_label = None
            field_required = field.get('required') is not None
            field_placeholder = field.get('placeholder', '')
            
            # Try to find associated label
            if field.get('id'):
                label = soup.find('label', {'for': field.get('id')})
                if label:
                    field_label = label.get_text(strip=True)
            
            # If no label found, look for nearby text
            if not field_label:
                # Look for text in parent elements
                parent = field.parent
                if parent:
                    text = parent.get_text(strip=True)
                    # Extract label-like text
                    if text and len(text) < 100:
                        field_label = text
            
            form_fields[field_name] = {
                "type": field_type,
                "label": field_label or field_name.replace('_', ' ').title(),
                "required": field_required,
                "placeholder": field_placeholder,
                "element_tag": field.name
            }
        
        # Store parsed fields in state
        state["form_fields"] = form_fields
        
        return {
            "success": True,
            "message": f"Successfully parsed form with {len(form_fields)} fields",
            "fields": form_fields
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to parse form: {str(e)}"
        }

@tool
def fetch_available_data(
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Fetch all available PII data and user profile information from identity manager.
    
    Args:
        state: Injected state containing identity_manager instance
    
    Returns:
        Dict with available PII data types and user profile info
    """
    try:
        identity_manager = get_identity_manager()
        
        if not identity_manager.verify_user():
            return {
                "success": False,
                "error": "User not authenticated in identity manager"
            }
        
        # Get all available PII data types
        available_pii_keys = identity_manager.get_all_pii_keys()
        if available_pii_keys is None:
            available_pii_keys = []
        
        # Get user profile information
        user_profile = identity_manager.fetch_user_profile_info()
        if user_profile is None:
            user_profile = {}
        
        # Compile available information
        available_data = {
            "pii_keys": available_pii_keys,
            "profile": user_profile,
        }
        
        # Store in state
        state["available_data"] = available_data
        
        return {
            "success": True,
            "message": f"Successfully retrieved available data. PII keys: {len(available_pii_keys)}, Profile fields: {len(user_profile)}",
            "available_data": available_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Data retrieval failed: {str(e)}"
        }

@tool
def generate_field_mapping(
    mapping_dict: Dict[str, str],
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Apply LLM-generated mapping to fetch actual data values for form fields.
    
    Args:
        mapping_dict: Dictionary mapping form field names to data source keys
        state: Injected state containing available_data
    
    Returns:
        Dict with mapped form data ready for filling
    """
    try:
        identity_manager = get_identity_manager()
        
        if not identity_manager.verify_user():
            return {
                "success": False,
                "error": "User not authenticated in identity manager"
            }
        
        form_fields = state.get("form_fields", {})
        available_data = state.get("available_data", {})
        
        if not form_fields:
            return {
                "success": False,
                "error": "No form fields available. Please parse the form first."
            }
        
        if not available_data:
            return {
                "success": False,
                "error": "No available data. Please fetch available data first."
            }
        
        form_data = {}
        filled_fields = []
        unfilled_fields = []
        
        # Get available data sources
        user_profile = available_data.get("profile", {})
        pii_keys = available_data.get("pii_keys", [])
        
        # Process each form field using the LLM-generated mapping
        for field_name, field_info in form_fields.items():
            field_value = None
            
            # Check if LLM provided a mapping for this field
            if field_name in mapping_dict:
                data_key = mapping_dict[field_name]
                
                # First try to get from user profile
                if data_key in user_profile:
                    field_value = user_profile[data_key]
                    print(f"Retrieved '{field_name}' from profile: {data_key}")
                
                # Then try PII storage
                elif data_key in pii_keys:
                    result = identity_manager.decrypt_pii_data(data_key)
                    if result.get("result"):
                        field_value = result["data"]
                        print(f"Retrieved '{field_name}' from PII storage: {data_key}")
                
                # Handle special cases like full name combination
                elif data_key == "full_name":
                    first_name = user_profile.get('first_name', '')
                    last_name = user_profile.get('last_name', '')
                    if first_name or last_name:
                        field_value = f"{first_name} {last_name}".strip()
                        print(f"Combined name for '{field_name}': {field_value}")
                
                if not field_value:
                    print(f"Mapping provided but no data found for '{field_name}' -> '{data_key}'")
            
            # Store result
            if field_value:
                form_data[field_name] = str(field_value)
                filled_fields.append(field_name)
            else:
                unfilled_fields.append(field_name)
        
        # Store in state
        state["form_data"] = form_data
        state["filled_fields"] = filled_fields
        state["unfilled_fields"] = unfilled_fields
        
        total_fields = len(form_fields)
        filled_count = len(filled_fields)
        
        return {
            "success": True,
            "message": f"Applied mapping and retrieved data for {filled_count}/{total_fields} form fields",
            "form_data": form_data,
            "filled_fields": filled_fields,
            "unfilled_fields": unfilled_fields,
            "all_fields_filled": len(unfilled_fields) == 0
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Mapping application failed: {str(e)}"
        }

@tool  
def get_mapping_info(
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Provide form fields and available data keys for LLM to generate mappings.
    
    Args:
        state: Injected state containing form_fields and available_data
    
    Returns:
        Dict with form fields info and available data keys for mapping
    """
    try:
        form_fields = state.get("form_fields", {})
        available_data = state.get("available_data", {})
        
        if not form_fields:
            return {
                "success": False,
                "error": "No form fields available. Please parse the form first."
            }
        
        if not available_data:
            return {
                "success": False,
                "error": "No available data. Please fetch available data first."
            }
        
        # Prepare form fields information
        form_info = {}
        for field_name, field_details in form_fields.items():
            form_info[field_name] = {
                "label": field_details.get("label", ""),
                "type": field_details.get("type", "text"),
                "required": field_details.get("required", False),
                "placeholder": field_details.get("placeholder", "")
            }
        
        # Prepare available data keys
        user_profile = available_data.get("profile", {})
        pii_keys = available_data.get("pii_keys", [])
        
        mapping_info = {
            "form_fields": form_info,
            "available_profile_keys": list(user_profile.keys()),
            "available_pii_keys": pii_keys,
            "special_combinations": {
                "full_name": "Combines first_name and last_name from profile"
            }
        }
        
        return {
            "success": True,
            "message": f"Prepared mapping info: {len(form_info)} form fields, {len(user_profile)} profile keys, {len(pii_keys)} PII keys",
            "mapping_info": mapping_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to prepare mapping info: {str(e)}"
        }

@tool
def fill_form(
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Fill form using Selenium with mapped data. Only submit if all fields are filled.
    
    Args:
        state: Injected state for browser session access and form data
    
    Returns:
        Dict with submission result and status
    """
    try:
        driver = state.get("browser_session")
        if not driver:
            return {
                "success": False,
                "error": "No browser session available. Please fetch the form first."
            }
        
        form_data = state.get("form_data", {})
        filled_fields_list = state.get("filled_fields", [])
        unfilled_fields_list = state.get("unfilled_fields", [])
        
        if not form_data:
            return {
                "success": False,
                "error": "No form data available. Please map the form fields first."
            }
        
        filled_fields = 0
        failed_fields = []
        
        # Fill each field with available data
        for field_name, field_value in form_data.items():
            try:
                # Try different ways to find the field
                element = None
                
                # Try by name attribute
                try:
                    element = driver.find_element(By.NAME, field_name)
                except NoSuchElementException:
                    pass
                
                # Try by id attribute
                if not element:
                    try:
                        element = driver.find_element(By.ID, field_name)
                    except NoSuchElementException:
                        pass
                
                # Try by placeholder text
                if not element:
                    try:
                        element = driver.find_element(By.XPATH, f"//input[@placeholder='{field_name}']")
                    except NoSuchElementException:
                        pass
                
                if element:
                    # Clear existing content and fill
                    element.clear()
                    element.send_keys(str(field_value))
                    filled_fields += 1
                    print(f"Filled field '{field_name}' with value '{field_value}'")
                else:
                    failed_fields.append(field_name)
                    print(f"Could not find field '{field_name}'")
                
            except Exception as e:
                failed_fields.append(field_name)
                print(f"Error filling field '{field_name}': {e}")
        
        # Wait a moment for any dynamic validation
        time.sleep(2)
        
        # Determine if we should submit the form
        should_submit = len(unfilled_fields_list) == 0
        submit_success = False
        submit_message = ""
        
        if should_submit:
            try:
                # Look for submit button
                submit_button = None
                
                # Try different submit button selectors
                submit_selectors = [
                    "input[type='submit']",
                    "button[type='submit']", 
                    "button[class*='submit']",
                    "input[value*='Submit']",
                    "button:contains('Submit')",
                    "input[class*='submit']"
                ]
                
                for selector in submit_selectors:
                    try:
                        if 'contains' in selector:
                            submit_button = driver.find_element(By.XPATH, f"//button[contains(text(), 'Submit')]")
                        else:
                            submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                        if submit_button:
                            break
                    except NoSuchElementException:
                        continue
                
                if submit_button:
                    # Scroll to submit button and click
                    driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                    time.sleep(1)
                    submit_button.click()
                    
                    # Wait for submission to process
                    time.sleep(3)
                    
                    # Check for success indicators
                    current_url = driver.current_url
                    page_source = driver.page_source.lower()
                    
                    success_indicators = [
                        'success', 'submitted', 'thank you', 'confirmation',
                        'complete', 'received', 'processed'
                    ]
                    
                    if any(indicator in page_source for indicator in success_indicators):
                        submit_success = True
                        submit_message = "Form appears to have been submitted successfully"
                    else:
                        submit_message = "Form submitted but success confirmation unclear"
                        submit_success = True  # Assume success if no error
                    
                else:
                    submit_message = "No submit button found on the form"
                    
            except Exception as e:
                submit_message = f"Error during form submission: {str(e)}"
        else:
            submit_message = f"Form not submitted - {len(unfilled_fields_list)} fields could not be filled: {unfilled_fields_list}. Form left open for manual completion."
            submit_success = False  # Don't close browser, let user complete manually
        
        # Store submission result
        submission_result = {
            "filled_fields": filled_fields,
            "failed_fields": failed_fields,
            "submit_success": submit_success,
            "submit_message": submit_message,
            "current_url": driver.current_url if driver else None,
            "unfilled_fields": unfilled_fields_list,
            "form_complete": len(unfilled_fields_list) == 0
        }
        
        state["form_submission_result"] = submission_result
        
        return {
            "success": True,  # Always return success if filling completed, regardless of submission
            "message": f"Form filling completed. Filled {filled_fields} fields. {submit_message}",
            "result": submission_result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Form filling failed: {str(e)}"
        }

# Bind tools to LLM
llm_with_tools = form_filler_llm.bind_tools([get_form, parse_form, fetch_available_data, generate_field_mapping, get_mapping_info, fill_form])

# Node Functions
def llm_orchestrator(state: FormFillerState) -> FormFillerState:
    """LLM orchestrator that decides which tools to call"""
    form_url = state.get("form_url", "")
    messages = state.get("messages", [])
    
    # Add system message if it's the first interaction
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        system_msg = SystemMessage(content=f"""You are a form filler agent. Your task is to:
1. Fetch the HTML content of the form at: {form_url}
2. Parse the form to understand what fields need to be filled
3. Fetch available user data (PII keys and profile information)
4. Get mapping information to understand available data keys and form fields
5. Generate intelligent mappings between form fields and user data keys
6. Apply the mappings to fetch actual data values
7. Fill the form with mapped data (only submit if ALL fields can be filled)

Available tools:
- get_form: Fetch HTML content from the form URL
- parse_form: Parse HTML to extract form fields and requirements  
- fetch_available_data: Get all available user data keys (PII keys, profile keys)
- get_mapping_info: Get form fields and available data keys for mapping analysis
- generate_field_mapping: Apply your mapping decisions to fetch actual data values
- fill_form: Fill the form with mapped data (submits only if all fields are filled)

MAPPING STRATEGY:
When calling generate_field_mapping, provide a dictionary mapping form field names to data source keys.
Examples:
- Form field "name" or "full_name" -> "full_name" (special combination)
- Form field "first_name" -> "first_name" (from profile)  
- Form field "phone" -> "phone" (from profile or PII)
- Form field "pan_number" -> "pan_number" (from PII)
- Form field "aadhar" -> "adhaar_number" (from PII)

IMPORTANT: Only submit the form if ALL required fields can be filled. If some fields cannot be filled, leave the form open for manual completion by the user.
MAKE SURE TO CALL ALL THE TOOLS IN THE CORRECT ORDER. DO NOT SKIP ANY TOOL CALL. 

Work step by step and call tools as needed.
""")
        messages = [system_msg]
    
    # Add user message if this is the start
    if len(messages) == 1:  # Only system message
        messages.append(HumanMessage(content=f"Please fill the form at {form_url}"))
    
    try:
        # Get LLM response
        response = llm_with_tools.invoke(messages)
        
        print(f"LLM Response: {response}")
        
        return {
            "messages": [response]
        }
    except Exception as e:
        error_msg = f"LLM orchestrator error: {str(e)}"
        return {
            "messages": [AIMessage(content=error_msg)],
            "error_message": error_msg
        }

def finalize_response(state: FormFillerState) -> FormFillerState:
    """Generate final report and cleanup resources"""
    try:
        # Generate final report
        submission_result = state.get("form_submission_result", {})
        error_message = state.get("error_message")
        
        if error_message:
            final_report = f"Form filling failed: {error_message}"
            # Clean up browser session on error
            browser_session = state.get("browser_session")
            if browser_session:
                try:
                    browser_session.quit()
                except Exception as e:
                    print(f"Error closing browser: {e}")
            return {
                "final_report": final_report,
                "browser_session": None
            }
        
        elif submission_result:
            filled_fields = submission_result.get('filled_fields', 0)
            unfilled_fields = submission_result.get('unfilled_fields', [])
            form_complete = submission_result.get('form_complete', False)
            
            if form_complete and submission_result.get("submit_success"):
                final_report = f"✅ Form successfully filled and submitted! All {filled_fields} fields were completed."
                # Clean up browser session after successful submission
                browser_session = state.get("browser_session")
                if browser_session:
                    try:
                        browser_session.quit()
                    except Exception as e:
                        print(f"Error closing browser: {e}")
                return {
                    "final_report": final_report,
                    "browser_session": None
                }
            
            elif not form_complete:
                final_report = f"📝 Form partially filled - {filled_fields} fields completed, {len(unfilled_fields)} fields need manual input.\n"
                final_report += f"Unfilled fields: {', '.join(unfilled_fields)}\n"
                final_report += "🖥️ Browser window left open for you to complete the remaining fields manually."
                # Keep browser session open for manual completion
                return {
                    "final_report": final_report
                }
            
            else:
                final_report = f"Form filled with {filled_fields} fields, but submission status unclear."
                # Keep browser open in case of uncertainty
                return {
                    "final_report": final_report
                }
        
        else:
            final_report = "Form filling process completed with unknown status."
            return {
                "final_report": final_report
            }
        
    except Exception as e:
        # Clean up browser session on exception
        browser_session = state.get("browser_session")
        if browser_session:
            try:
                browser_session.quit()
            except Exception as e2:
                print(f"Error closing browser: {e2}")
        
        return {
            "final_report": f"Error during finalization: {str(e)}",
            "error_message": str(e),
            "browser_session": None
        }

# Graph Builder Function
def create_form_filler_graph():
    """Create and compile the form filler graph"""
    builder = StateGraph(
        FormFillerState,
        input_schema=FormFillerInputState,
        output_schema=FormFillerOutputState
    )
    
    # Add nodes
    builder.add_node("llm_orchestrator", llm_orchestrator)
    builder.add_node("tools", ToolNode([get_form, parse_form, fetch_available_data, generate_field_mapping, get_mapping_info, fill_form]))
    builder.add_node("finalize_response", finalize_response)
    
    # Add edges
    builder.add_edge(START, "llm_orchestrator")
    builder.add_conditional_edges("llm_orchestrator", tools_condition)
    builder.add_edge("tools", "llm_orchestrator") 
    builder.add_edge("finalize_response", END)
    
    return builder.compile()

# Tool function to be used by the main agent
@tool
def fill_web_form(
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """
    Fill and submit a web form automatically using a ReAct agent.
    Hardcoded to use the demo form on localhost:5500 for testing.
    
    Args:
        state: Injected state containing session info and identity_manager
    
    Returns:
        Dict with success status, final report, and submission details
    """
    try:
        # Hardcoded demo form URL
        form_url = "http://localhost:5500/test_form.html"
        
        # Create form filler graph
        form_filler_graph = create_form_filler_graph()
        
        # Run the graph
        result = form_filler_graph.invoke(
            {"form_url": form_url,
             "identity_manager": state.get("identity_manager")}
        )
        
        return {
            "success": result.get("final_report", "").startswith("Form successfully"),
            "final_report": result.get("final_report", "Form filling completed"),
            "submission_result": result.get("form_submission_result"),
            "demo_url": form_url
        }
        
    except Exception as e:
        return {
            "success": False,
            "final_report": f"Form filler agent failed: {str(e)}",
            "error": str(e),
            "demo_url": "http://localhost:5500/test_form.html"
        } 