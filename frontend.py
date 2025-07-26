import streamlit as st
import pyttsx3
import sounddevice as sd
import numpy as np
import time
from saarthi_assistant.voice.main import transcribe_audio_numpy

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Saarthi - Government Scheme Assistant",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ENHANCED CSS for modern, appealing UI ---
st.markdown("""
<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global styling with improved background */
.appview-container, .main, body, html {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    min-height: 100vh !important;
    font-family: 'Inter', sans-serif !important;
}

/* Main container with glass morphism effect */
.main > div {
    background: rgba(255, 255, 255, 0.1) !important;
    backdrop-filter: blur(20px) !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    margin: 20px !important;
    padding: 30px !important;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1) !important;
}

/* Header styling with better typography */
.main-header {
    margin: 0 0 30px 0 !important;
    padding: 20px 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 3rem !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    text-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.1)) !important;
    border-radius: 20px !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

.main-header .emoji {
    font-size: 3.5rem !important;
    margin-right: 15px !important;
    filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2)) !important;
}

/* Chat container styling */
.chat-wrapper {
    min-height: 400px !important;
    margin: 20px 0 !important;
    background: rgba(255, 255, 255, 0.05) !important;
    border-radius: 20px !important;
    padding: 20px !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* Question bubbles with improved styling */
.question-bubbles-container {
    margin-bottom: 25px !important;
    padding: 15px 0 !important;
    gap: 15px !important;
    display: flex !important;
    flex-wrap: wrap !important;
    justify-content: center !important;
}

/* Enhanced button styling */
.stButton > button {
    background: linear-gradient(135deg, #ff6b9d, #c44569) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 25px !important;
    padding: 12px 20px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    min-width: 140px !important;
    height: 45px !important;
    box-shadow: 0 8px 25px rgba(255, 107, 157, 0.3) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    text-transform: none !important;
    letter-spacing: 0.5px !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 35px rgba(255, 107, 157, 0.4) !important;
    background: linear-gradient(135deg, #ff5e94, #b73e5e) !important;
}

.stButton > button:active {
    transform: translateY(0px) !important;
    box-shadow: 0 5px 15px rgba(255, 107, 157, 0.3) !important;
}

/* Messages container with better scrolling */
.messages-container {
    max-height: 400px !important;
    min-height: 150px !important;
    overflow-y: auto !important;
    padding: 20px !important;
    background: rgba(255, 255, 255, 0.03) !important;
    border-radius: 15px !important;
    margin-bottom: 20px !important;
    scroll-behavior: smooth !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* Custom scrollbar */
.messages-container::-webkit-scrollbar {
    width: 6px !important;
}

.messages-container::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1) !important;
    border-radius: 3px !important;
}

.messages-container::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3) !important;
    border-radius: 3px !important;
}

/* Enhanced message bubbles */
.user-message {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: #ffffff !important;
    padding: 16px 22px !important;
    border-radius: 25px 25px 8px 25px !important;
    margin: 15px 0 15px auto !important;
    max-width: 75% !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3) !important;
    animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    line-height: 1.5 !important;
}

.bot-message {
    background: linear-gradient(135deg, #ff6b9d, #c44569) !important;
    color: #ffffff !important;
    padding: 16px 22px !important;
    border-radius: 25px 25px 25px 8px !important;
    margin: 15px auto 15px 0 !important;
    max-width: 75% !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    box-shadow: 0 8px 25px rgba(255, 107, 157, 0.3) !important;
    animation: slideInLeft 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    line-height: 1.5 !important;
}

/* Improved animations */
@keyframes slideInRight {
    from {
        transform: translateX(50px) scale(0.9);
        opacity: 0;
    }
    to {
        transform: translateX(0) scale(1);
        opacity: 1;
    }
}

@keyframes slideInLeft {
    from {
        transform: translateX(-50px) scale(0.9);
        opacity: 0;
    }
    to {
        transform: translateX(0) scale(1);
        opacity: 1;
    }
}

/* Input area styling */
.input-area {
    background: rgba(255, 255, 255, 0.1) !important;
    border-radius: 20px !important;
    padding: 20px !important;
    margin-top: 20px !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
}

/* Mic button special styling */
#mic_btn {
    background: linear-gradient(135deg, #4facfe, #00f2fe) !important;
    font-size: 16px !important;
    padding: 15px 30px !important;
    min-width: 160px !important;
    height: 55px !important;
    box-shadow: 0 10px 30px rgba(79, 172, 254, 0.4) !important;
}

#mic_btn:hover {
    background: linear-gradient(135deg, #43a3f5, #00d9e7) !important;
    box-shadow: 0 15px 40px rgba(79, 172, 254, 0.5) !important;
}

/* Streamlit info/success/error styling */
.stAlert {
    border-radius: 15px !important;
    border: none !important;
    backdrop-filter: blur(10px) !important;
    font-weight: 500 !important;
}

.stAlert > div {
    background: rgba(255, 255, 255, 0.95) !important;
    color: #333 !important;
    border-radius: 15px !important;
    padding: 15px 20px !important;
}

/* Footer styling */
.footer {
    text-align: center !important;
    color: rgba(255, 255, 255, 0.8) !important;
    padding: 20px !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    background: rgba(255, 255, 255, 0.05) !important;
    border-radius: 15px !important;
    margin-top: 30px !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* Spinner customization */
.stSpinner > div {
    border-color: #667eea transparent #667eea transparent !important;
}

/* Block container improvements */
.block-container {
    padding: 2rem 1rem !important;
    max-width: 1000px !important;
}

/* Remove Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
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

# --- HEADER ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)
st.markdown(
    '<h1 class="main-header">'
    '<span class="emoji">🧭</span> '
    'Saarthi'
    '</h1>', unsafe_allow_html=True,
)

# --- Question Bubbles ---
st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)
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
            st.session_state.messages.append({"type": "user", "content": q})
            st.session_state.messages.append({"type": "bot", "content": responses[i]})
            selected_bubble_reply = responses[i]
            st.session_state.pending_tts = responses[i]

st.markdown('</div>', unsafe_allow_html=True)

# --- Chat Messages ---
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

# --- Input area with mic button ---
st.markdown('<div class="input-area">', unsafe_allow_html=True)
mic_button = st.button("🎙 Speak to Saarthi", key="mic_btn", help="Click to speak your question")
st.markdown('</div>', unsafe_allow_html=True)

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
            else:
                # Transcribe using voice service
                user_input = transcribe_with_voice_service(audio_array, sample_rate)
                
                if user_input and user_input.strip():
                    st.session_state.messages.append({"type": "user", "content": user_input})
                    standard_reply = "Thank you for your question. I am processing your request and will get back to you shortly."
                    st.session_state.messages.append({"type": "bot", "content": standard_reply})
                    st.success(f"You said: {user_input}")
                    st.session_state.pending_tts = standard_reply
                else:
                    error_msg = "Sorry, I couldn't understand that. Please try again."
                    st.error(error_msg)
                    st.session_state.pending_tts = error_msg
        else:
            error_msg = "Recording failed. Please check your microphone and try again."
            st.error(error_msg)
            st.session_state.pending_tts = error_msg
            
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}. Please try again."
        st.error(error_msg)
        st.session_state.pending_tts = error_msg

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