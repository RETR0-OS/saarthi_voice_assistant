from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pyttsx3
import sounddevice as sd
import numpy as np
import time
import uuid
from saarthi_assistant.voice.main import transcribe_audio_numpy
from saarthi_assistant.sub_graphs.graph_runner import (
    run_authentication, 
    submit_registration_data, 
    submit_pii_data, 
    reset_authentication,
    start_agent_conversation,
    send_agent_message,
    end_agent_conversation
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Saarthi - Government Scheme Assistant",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ENHANCED CSS for warm, subtle UI ---
st.markdown("""
<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@300;400;500;600&display=swap');

/* Global styling with warm, light background */
.appview-container, .main, body, html {
    background: linear-gradient(135deg, #f7f1e8 0%, #ede4d3 50%, #f2e7dc 100%) !important;
    min-height: 100vh !important;
    font-family: 'Inter', sans-serif !important;
}

/* Main container with subtle glass effect */
.main > div {
    background: rgba(255, 251, 247, 0.85) !important;
    backdrop-filter: blur(12px) !important;
    border-radius: 24px !important;
    border: 1px solid rgba(210, 180, 160, 0.2) !important;
    margin: 16px !important;
    padding: 24px !important;
    box-shadow: 0 8px 32px rgba(139, 115, 98, 0.08) !important;
}

/* Header styling with warm tones */
.main-header {
    margin: 0 0 20px 0 !important;
    padding: 20px 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 2.8rem !important;
    font-weight: 600 !important;
    font-family: 'Poppins', sans-serif !important;
    color: #5d4e37 !important;
    text-shadow: 0 2px 8px rgba(93, 78, 55, 0.1) !important;
    background: linear-gradient(135deg, rgba(245, 230, 210, 0.8), rgba(240, 220, 200, 0.6)) !important;
    border-radius: 20px !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(210, 180, 160, 0.3) !important;
}

.main-header .emoji {
    font-size: 3rem !important;
    margin-right: 12px !important;
    filter: drop-shadow(0 2px 6px rgba(93, 78, 55, 0.15)) !important;
}

/* Chat container styling */
.chat-wrapper {
    min-height: 200px !important;
    margin: 16px 0 !important;
    background: rgba(252, 248, 243, 0.7) !important;
    border-radius: 20px !important;
    padding: 20px !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(210, 180, 160, 0.2) !important;
    box-shadow: inset 0 2px 8px rgba(139, 115, 98, 0.04) !important;
}

/* Question bubbles with warm styling */
.question-bubbles-container {
    margin-bottom: 16px !important;
    padding: 8px 0 !important;
    gap: 12px !important;
    display: flex !important;
    flex-wrap: wrap !important;
    justify-content: center !important;
}

/* Enhanced button styling with warm colors */
.stButton > button {
    background: linear-gradient(135deg, #d4a574, #c49363) !important;
    color: #4a3728 !important;
    border: none !important;
    border-radius: 18px !important;
    padding: 12px 18px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    min-width: 135px !important;
    height: 44px !important;
    box-shadow: 0 4px 16px rgba(196, 147, 99, 0.25) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    text-transform: none !important;
    letter-spacing: 0.3px !important;
}

.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(196, 147, 99, 0.35) !important;
    background: linear-gradient(135deg, #c49363, #b08752) !important;
}

.stButton > button:active {
    transform: translateY(0px) !important;
    box-shadow: 0 3px 12px rgba(196, 147, 99, 0.25) !important;
}

/* Messages container with subtle styling */
.messages-container {
    max-height: 300px !important;
    min-height: 100px !important;
    overflow-y: auto !important;
    padding: 16px !important;
    background: rgba(255, 253, 250, 0.6) !important;
    border-radius: 16px !important;
    margin-bottom: 16px !important;
    scroll-behavior: smooth !important;
    border: 1px solid rgba(210, 180, 160, 0.15) !important;
}

/* Custom scrollbar with warm tones */
.messages-container::-webkit-scrollbar {
    width: 6px !important;
}

.messages-container::-webkit-scrollbar-track {
    background: rgba(210, 180, 160, 0.1) !important;
    border-radius: 3px !important;
}

.messages-container::-webkit-scrollbar-thumb {
    background: rgba(196, 147, 99, 0.4) !important;
    border-radius: 3px !important;
}

/* Enhanced message bubbles with warm colors */
.user-message {
    background: linear-gradient(135deg, #e8d5b7, #dcc5a3) !important;
    color: #3d2f1f !important;
    padding: 16px 20px !important;
    border-radius: 20px 20px 6px 20px !important;
    margin: 12px 0 12px auto !important;
    max-width: 78% !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    box-shadow: 0 3px 12px rgba(139, 115, 98, 0.15) !important;
    animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid rgba(180, 150, 120, 0.2) !important;
    line-height: 1.5 !important;
}

.bot-message {
    background: linear-gradient(135deg, #f5e6d3, #ede0d0) !important;
    color: #2d1f12 !important;
    padding: 16px 20px !important;
    border-radius: 20px 20px 20px 6px !important;
    margin: 12px auto 12px 0 !important;
    max-width: 78% !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    box-shadow: 0 3px 12px rgba(139, 115, 98, 0.12) !important;
    animation: slideInLeft 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid rgba(160, 130, 100, 0.15) !important;
    line-height: 1.5 !important;
}

/* Improved animations */
@keyframes slideInRight {
    from {
        transform: translateX(30px) scale(0.95);
        opacity: 0;
    }
    to {
        transform: translateX(0) scale(1);
        opacity: 1;
    }
}

@keyframes slideInLeft {
    from {
        transform: translateX(-30px) scale(0.95);
        opacity: 0;
    }
    to {
        transform: translateX(0) scale(1);
        opacity: 1;
    }
}

/* Input area styling */
.input-area {
    background: rgba(248, 240, 230, 0.8) !important;
    border-radius: 20px !important;
    padding: 16px !important;
    margin-top: 16px !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(210, 180, 160, 0.25) !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
}

/* Mic button special styling */
#mic_btn {
    background: linear-gradient(135deg, #8b7355, #76634a) !important;
    color: #ffffff !important;
    font-size: 16px !important;
    padding: 16px 32px !important;
    min-width: 180px !important;
    height: 56px !important;
    box-shadow: 0 6px 20px rgba(139, 115, 85, 0.3) !important;
    font-weight: 600 !important;
}

#mic_btn:hover {
    background: linear-gradient(135deg, #76634a, #68573f) !important;
    box-shadow: 0 8px 24px rgba(139, 115, 85, 0.4) !important;
}

/* Streamlit info/success/error styling */
.stAlert {
    border-radius: 12px !important;
    border: none !important;
    backdrop-filter: blur(8px) !important;
    font-weight: 500 !important;
    margin: 8px 0 !important;
}

.stAlert > div {
    background: rgba(255, 251, 247, 0.95) !important;
    color: #3d2f1f !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    border: 1px solid rgba(180, 150, 120, 0.2) !important;
}

.stAlert[data-baseweb="notification"][data-testid="stNotificationContentSuccess"] > div {
    background: rgba(220, 240, 210, 0.95) !important;
    color: #2d4a1f !important;
    border: 1px solid rgba(120, 180, 100, 0.3) !important;
}

.stAlert[data-baseweb="notification"][data-testid="stNotificationContentError"] > div {
    background: rgba(255, 235, 230, 0.95) !important;
    color: #4a1f1f !important;
    border: 1px solid rgba(200, 100, 100, 0.3) !important;
}

.stAlert[data-baseweb="notification"][data-testid="stNotificationContentWarning"] > div {
    background: rgba(255, 245, 220, 0.95) !important;
    color: #4a3a1f !important;
    border: 1px solid rgba(200, 160, 80, 0.3) !important;
}

/* Footer styling */
.footer {
    text-align: center !important;
    color: #6d5d47 !important;
    padding: 16px !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    background: rgba(245, 235, 220, 0.6) !important;
    border-radius: 16px !important;
    margin-top: 20px !important;
    backdrop-filter: blur(6px) !important;
    border: 1px solid rgba(180, 150, 120, 0.2) !important;
}

/* Spinner customization */
.stSpinner > div {
    border-color: #c49363 transparent #c49363 transparent !important;
}

/* Block container improvements */
.block-container {
    padding: 1.5rem 1rem !important;
    max-width: 980px !important;
}

/* Remove Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Typography improvements */
.stMarkdown {
    color: #3d2f1f !important;
}

/* Enhanced focus states */
.stButton > button:focus {
    outline: 2px solid rgba(139, 115, 85, 0.5) !important;
    outline-offset: 2px !important;
}
</style>
""", unsafe_allow_html=True)

# --- Audio Recording Functions ---
def record_audio(duration=5, sample_rate=16000):
    """Record audio using sounddevice and return as numpy array"""
    try:
        st.info("🎙️ Recording... Please speak now!")
        
        # Record audio
        recording = sd.rec(int(duration * sample_rate), 
                          samplerate=sample_rate, 
                          channels=1, 
                          dtype=np.float32)
        sd.wait()  # Wait until recording is finished
        
        # Normalize audio to prevent clipping
        recording = recording.flatten()
        if np.max(np.abs(recording)) > 0:
            recording = recording / np.max(np.abs(recording)) * 0.8
        
        return recording, sample_rate
    except Exception as e:
        st.error(f"Recording failed: {str(e)}")
        return None, None

def transcribe_with_voice_service(audio_array, sample_rate=16000):
    """Transcribe audio using the voice service"""
    try:
        with st.spinner("🤖 Processing your speech..."):
            start_time = time.time()
            result = transcribe_audio_numpy(audio_array, sample_rate)
            processing_time = time.time() - start_time
            
            if result["success"]:
                st.success(f"✅ Transcription completed in {processing_time:.2f}s")
                return result["text"]
            else:
                st.error(f"❌ Transcription failed: {result['error']}")
                return None
    except Exception as e:
        st.error(f"Voice service error: {str(e)}")
        return None

# --- TTS engine ---
def init_tts():
    if 'engine' not in st.session_state:
        st.session_state.engine = pyttsx3.init()
        try:
            voices = st.session_state.engine.getProperty('voices')
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    st.session_state.engine.setProperty('voice', voice.id)
                    break
            st.session_state.engine.setProperty('rate', 150)
        except Exception:
            pass

def speak(text):
    try:
        if 'engine' in st.session_state:
            st.session_state.engine.say(text)
            st.session_state.engine.runAndWait()
    except Exception:
        pass

init_tts()

# --- Authentication Form Functions ---
def show_registration_form():
    """Display registration form for new users"""
    st.markdown("### 📝 New User Registration")
    st.markdown("Please fill in your details to create an account:")
    
    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name *", placeholder="Enter your first name")
        with col2:
            last_name = st.text_input("Last Name", placeholder="Enter your last name (optional)")
        
        dob = st.date_input("Date of Birth *")
        phone = st.text_input("Phone Number *", placeholder="Enter your 10-digit phone number")
        
        submitted = st.form_submit_button("📷 Register & Capture Face", use_container_width=True)
        
        if submitted:
            if not first_name or not phone:
                st.error("Please fill in all required fields (marked with *)")
                return
            
            if len(phone) != 10 or not phone.isdigit():
                st.error("Please enter a valid 10-digit phone number")
                return
            
            registration_data = {
                "first_name": first_name,
                "last_name": last_name if last_name else "",
                "dob": str(dob),
                "phone": phone
            }
            
            with st.spinner("🤖 Processing registration..."):
                result = submit_registration_data(registration_data)
            
            if result["success"]:
                if result.get("requires_pii"):
                    st.session_state.show_registration_form = False
                    st.session_state.show_pii_form = True
                    st.success("Registration successful! Now please provide your documents.")
                    st.rerun()
                elif result["auth_result"]:
                    st.session_state.user_authenticated = True
                    st.session_state.current_mode = "agent"
                    st.session_state.show_registration_form = False
                    st.success(result["notes"])
                    st.rerun()
                else:
                    st.error(result["notes"])
            else:
                st.error(result["notes"])

def show_pii_form():
    """Display PII collection form"""
    st.markdown("### 🏛️ Government Documents & Information")
    st.markdown("Please provide your government documents for scheme applications. You can leave any field empty if you don't have that document.")
    
    with st.form("pii_form"):
        st.markdown("#### Required Documents")
        col1, col2 = st.columns(2)
        with col1:
            adhaar_number = st.text_input("Aadhaar Number", placeholder="12-digit Aadhaar number")
        with col2:
            pan_number = st.text_input("PAN Number", placeholder="10-character PAN number")
        
        with st.expander("📄 Optional Government IDs"):
            col3, col4 = st.columns(2)
            with col3:
                voter_id = st.text_input("Voter ID", placeholder="Voter ID number")
                driving_license = st.text_input("Driving License", placeholder="DL number")
            with col4:
                passport_number = st.text_input("Passport Number", placeholder="Passport number")
        
        with st.expander("🏦 Banking Information"):
            col5, col6 = st.columns(2)
            with col5:
                bank_account_number = st.text_input("Bank Account Number", placeholder="Account number")
            with col6:
                ifsc_code = st.text_input("IFSC Code", placeholder="Bank IFSC code")
        
        with st.expander("📜 Certificates"):
            income_certificate = st.text_input("Income Certificate Number", placeholder="Certificate number")
            caste_certificate = st.text_input("Caste Certificate Number", placeholder="Certificate number")
            domicile_certificate = st.text_input("Domicile Certificate Number", placeholder="Certificate number")
            disability_certificate = st.text_input("Disability Certificate Number", placeholder="Certificate number")
        
        submitted = st.form_submit_button("🔐 Complete Registration", use_container_width=True)
        
        if submitted:
            pii_data = {
                "adhaar_number": adhaar_number,
                "pan_number": pan_number,
                "voter_id": voter_id,
                "driving_license": driving_license,
                "passport_number": passport_number,
                "bank_account_number": bank_account_number,
                "ifsc_code": ifsc_code,
                "income_certificate_number": income_certificate,
                "caste_certificate_number": caste_certificate,
                "domicile_certificate_number": domicile_certificate,
                "disability_certificate_number": disability_certificate
            }
            
            with st.spinner("🔐 Encrypting and storing your information..."):
                result = submit_pii_data(pii_data)
            
            if result["success"] and result["auth_result"]:
                st.session_state.user_authenticated = True
                st.session_state.current_mode = "agent"
                st.session_state.show_pii_form = False
                # Start agent conversation for new user
                user_id = st.session_state.user_id or str(uuid.uuid4())
                st.session_state.user_id = user_id
                st.session_state.agent_thread_id = start_agent_conversation(user_id)
                st.success("🎉 Registration complete! Welcome to Saarthi!")
                st.balloons()
                st.rerun()
            else:
                st.error(result["notes"])

# --- Session state init ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "greeted" not in st.session_state:
    greeting = ("Hello! I am Saarthi, your intelligent government scheme assistant. "
                "I can help you discover and learn about various government schemes and programs.")
    st.session_state.greeted = True
    st.session_state.messages.append({"type": "bot", "content": greeting})
    st.session_state.pending_tts = greeting
if "is_typing" not in st.session_state:
    st.session_state.is_typing = False

# --- Authentication session state ---
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "auth"  # Start with authentication
if "auth_in_progress" not in st.session_state:
    st.session_state.auth_in_progress = False
if "show_registration_form" not in st.session_state:
    st.session_state.show_registration_form = False
if "show_pii_form" not in st.session_state:
    st.session_state.show_pii_form = False
if "auth_notes" not in st.session_state:
    st.session_state.auth_notes = ""

# --- Agent conversation state ---
if "agent_thread_id" not in st.session_state:
    st.session_state.agent_thread_id = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# --- HEADER ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)
st.markdown(
    '<h1 class="main-header">'
    '<span class="emoji">🧭</span> '
    'Saarthi'
    '</h1>', unsafe_allow_html=True,
)

# --- Main Content Area ---
st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

# Check authentication status and show appropriate interface
if not st.session_state.user_authenticated:
    # --- AUTHENTICATION INTERFACE ---
    st.markdown('<div class="question-bubbles-container">', unsafe_allow_html=True)
    
    # Show authentication status message
    if st.session_state.auth_notes:
        if "successful" in st.session_state.auth_notes.lower():
            st.success(st.session_state.auth_notes)
        else:
            st.info(st.session_state.auth_notes)
    
    # Authentication button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔐 Authenticate with Face", key="auth_btn", help="Click to authenticate using face recognition", use_container_width=True):
            st.session_state.auth_in_progress = True
            with st.spinner("🤖 Initializing camera and authentication..."):
                result = run_authentication()
            
            st.session_state.auth_in_progress = False
            
            if result["success"]:
                if result["auth_result"]:
                    # Successful authentication
                    st.session_state.user_authenticated = True
                    st.session_state.current_mode = "agent"
                    st.session_state.auth_notes = result["notes"]
                    # Start agent conversation
                    user_id = result.get("user_id", str(uuid.uuid4()))
                    st.session_state.user_id = user_id
                    st.session_state.agent_thread_id = start_agent_conversation(user_id)
                    st.success(result["notes"])
                    st.rerun()
                elif result.get("requires_registration"):
                    # Need registration
                    st.session_state.show_registration_form = True
                    st.session_state.auth_notes = result["notes"]
                    st.info("Face not recognized. Please register as a new user.")
                    st.rerun()
                else:
                    # Authentication failed
                    st.error(result["notes"])
                    st.session_state.auth_notes = result["notes"]
            else:
                st.error(result["notes"])
                st.session_state.auth_notes = result["notes"]
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show forms if needed
    if st.session_state.show_registration_form:
        show_registration_form()
    elif st.session_state.show_pii_form:
        show_pii_form()
    
    # Show informational message
    if not st.session_state.show_registration_form and not st.session_state.show_pii_form:
        st.markdown('<div style="text-align: center; margin: 20px 0; color: #6d5d47;">', unsafe_allow_html=True)
        st.markdown("👋 **Welcome to Saarthi!**")
        st.markdown("Please authenticate with your face to access government scheme assistance.")
        st.markdown("If you're a new user, you'll be guided through a quick registration process.")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- AGENT INTERFACE (existing functionality) ---
    st.markdown('<div class="question-bubbles-container">', unsafe_allow_html=True)
    
    questions = [
        "🏠 Housing Schemes",
        "💰 Pension Info",
        "🎓 Education Benefits",
        "🌾 Farmer Schemes"
    ]
    responses = [
        "The Pradhan Mantri Awas Yojana (PM Housing Scheme) provides affordable housing for economically weaker sections. You need Aadhaar card and income certificate to apply. Visit your nearest government office for more details.",
        "Old Age Pension Scheme provides monthly pension after 60 years of age. The National Social Assistance Programme covers various pension schemes. Apply at your nearest Anganwadi center or Tehsil office.",
        "Various education schemes like scholarships for girls, mid-day meal program, and free textbooks are available. Contact your school or education department for specific scheme details.",
        "PM Kisan Scheme provides ₹6000 annually to eligible farmers. You need land documents and Aadhaar card. Also, Crop Insurance Scheme protects against crop losses. Visit your nearest agriculture office."
    ]
    
    selected_bubble_reply = None
    cols = st.columns(len(questions))
    for i, q in enumerate(questions):
        with cols[i]:
            if st.button(q, key=f"bubble_{i}", help="Click to ask this question and hear the answer aloud"):
                # Send question to agent graph
                with st.spinner("🤖 Processing your query..."):
                    result = send_agent_message(q, st.session_state.agent_thread_id)
                
                if result["success"]:
                    st.session_state.messages.append({"type": "user", "content": q})
                    st.session_state.messages.append({"type": "bot", "content": result["response"]})
                    st.session_state.pending_tts = result["response"]
                    
                    # Check if session is still valid
                    if not result.get("session_valid", True):
                        st.warning("Session expired. Please re-authenticate.")
                        st.session_state.user_authenticated = False
                        st.rerun()
                else:
                    st.error(result["response"])
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- Chat Messages (only for authenticated users) ---
if st.session_state.user_authenticated:
    st.markdown('<div class="messages-container" id="chat-messages">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        if message["type"] == "user":
            st.markdown(f'<div class="user-message">👤 {message["content"]}</div>', unsafe_allow_html=True)
        elif message["type"] == "bot":
            st.markdown(f'<div class="bot-message">🤖 {message["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Auto scroll chat ---
st.markdown("""
<script>
setTimeout(function() {
    var msgbox = document.getElementById('chat-messages');
    if(msgbox) { msgbox.scrollTop = msgbox.scrollHeight; }
}, 100);
</script>
""", unsafe_allow_html=True)

# --- Input area with mic button (only for authenticated users) ---
if st.session_state.user_authenticated:
    st.markdown('<div class="input-area">', unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    with col1:
        mic_button = st.button("🎙 Speak to Saarthi", key="mic_btn", help="Click to speak your question", use_container_width=True)
    with col2:
        if st.button("🚪 Logout", key="logout_btn", help="Logout and clear session", use_container_width=True):
            # Reset session state
            st.session_state.user_authenticated = False
            st.session_state.current_mode = "auth"
            st.session_state.auth_notes = ""
            st.session_state.show_registration_form = False
            st.session_state.show_pii_form = False
            st.session_state.messages = []
            st.session_state.agent_thread_id = None
            st.session_state.user_id = None
            end_agent_conversation()
            reset_authentication()
            st.success("Logged out successfully!")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
else:
    mic_button = False  # Disable mic functionality when not authenticated

if mic_button:
    try:
        speak("Yes, I'm listening.")
        
        # Record audio using sounddevice
        audio_array, sample_rate = record_audio(duration=5, sample_rate=16000)
        
        if audio_array is not None:
            # Check if audio has enough signal
            if np.max(np.abs(audio_array)) < 0.01:
                error_msg = "No speech detected. Please speak louder and try again."
                st.warning(error_msg)
                st.session_state.pending_tts = error_msg
                st.rerun()  # Force update for warning message
            else:
                # Transcribe using voice service
                user_input = transcribe_with_voice_service(audio_array, sample_rate)
                
                if user_input and user_input.strip():
                    # Send transcribed text to agent graph
                    with st.spinner("🤖 Processing your query..."):
                        result = send_agent_message(user_input, st.session_state.agent_thread_id)
                    
                    if result["success"]:
                        st.session_state.messages.append({"type": "user", "content": user_input})
                        st.session_state.messages.append({"type": "bot", "content": result["response"]})
                        st.success(f"You said: {user_input}")
                        st.session_state.pending_tts = result["response"]
                        
                        # Check if session is still valid
                        if not result.get("session_valid", True):
                            st.warning("Session expired. Please re-authenticate.")
                            st.session_state.user_authenticated = False
                            st.rerun()
                    else:
                        error_msg = result["response"]
                        st.error(error_msg)
                        st.session_state.pending_tts = error_msg
                    st.rerun()  # Force update to show new messages
                else:
                    error_msg = "Sorry, I couldn't understand that. Please try again."
                    st.error(error_msg)
                    st.session_state.pending_tts = error_msg
                    st.rerun()  # Force update for error message
        else:
            error_msg = "Recording failed. Please check your microphone and try again."
            st.error(error_msg)
            st.session_state.pending_tts = error_msg
            st.rerun()  # Force update for error message
            
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}. Please try again."
        st.error(error_msg)
        st.session_state.pending_tts = error_msg
        st.rerun()  # Force update for exception error

# --- AFTER ALL UI, run TTS if pending ---
if 'pending_tts' in st.session_state:
    speak(st.session_state['pending_tts'])
    del st.session_state['pending_tts']

# --- Footer ---
st.markdown("---", unsafe_allow_html=True)
st.markdown(
    '<div class="footer">'
    '🌟 Saarthi - Your intelligent guide to government schemes | Powered by AI | Completely Free'
    '</div>',
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)