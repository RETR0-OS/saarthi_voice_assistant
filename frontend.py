import streamlit as st
import pyttsx3
import speech_recognition as sr
import os
import time

# Page configuration
st.set_page_config(
    page_title="Scheme Assistant", 
    page_icon="🏠",
    layout="wide"
)

# Custom CSS for warm, friendly design
st.markdown("""
<style>
    /* Main background with warm gradient */
    .stApp {
        background: linear-gradient(135deg, #FFF8E1 0%, #FFE0B2 100%);
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #FF8A65, #FFAB40);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 20px;
        font-family: 'Arial', sans-serif;
    }
    
    /* Chat container */
    .chat-container {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 8px 32px rgba(255, 138, 101, 0.2);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        min-height: 400px;
        max-height: 400px;
        overflow-y: auto;
    }
    
    /* Message bubbles */
    .user-message {
        background: linear-gradient(135deg, #4CAF50, #66BB6A);
        color: white;
        padding: 12px 20px;
        border-radius: 20px 20px 5px 20px;
        margin: 10px 0 10px auto;
        max-width: 80%;
        display: block;
        width: fit-content;
        margin-left: auto;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
        font-size: 16px;
    }
    
    .bot-message {
        background: linear-gradient(135deg, #FF8A65, #FFAB40);
        color: white;
        padding: 12px 20px;
        border-radius: 20px 20px 20px 5px;
        margin: 10px auto 10px 0;
        max-width: 80%;
        display: block;
        width: fit-content;
        box-shadow: 0 4px 12px rgba(255, 138, 101, 0.3);
        font-size: 16px;
    }
    
    /* Input area styling */
    .input-area {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 25px;
        padding: 15px;
        margin-top: 20px;
        box-shadow: 0 8px 32px rgba(255, 138, 101, 0.15);
        border: 2px solid rgba(255, 171, 64, 0.3);
    }
    
    /* Streamlit button styling */
    .stButton > button {
        background: linear-gradient(135deg, #E91E63, #F06292) !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 15px 30px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 6px 20px rgba(233, 30, 99, 0.3) !important;
        width: 100% !important;
        height: 60px !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(233, 30, 99, 0.4) !important;
    }
    
    /* Question button styling */
    div[data-testid="column"] .stButton > button {
        background: linear-gradient(135deg, #FFE082, #FFCC02) !important;
        color: #5D4037 !important;
        border-radius: 25px !important;
        padding: 10px 15px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        margin: 8px 0 !important;
        height: auto !important;
        min-height: 50px !important;
        box-shadow: 0 4px 15px rgba(255, 204, 2, 0.3) !important;
    }
    
    div[data-testid="column"] .stButton > button:hover {
        background: linear-gradient(135deg, #FFF176, #FFD54F) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 204, 2, 0.4) !important;
    }
    
    /* Text input styling */
    .stTextInput > div > div > input {
        font-size: 16px !important;
        padding: 15px !important;
        border-radius: 15px !important;
        border: 2px solid rgba(255, 171, 64, 0.3) !important;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #FFF3E0 0%, #FFE0B2 100%) !important;
    }
    
    /* Success/Error message styling */
    .stSuccess {
        background: linear-gradient(135deg, #4CAF50, #66BB6A) !important;
        color: white !important;
        border-radius: 15px !important;
        padding: 15px !important;
        font-size: 16px !important;
    }
    
    .stError {
        background: linear-gradient(135deg, #F44336, #E57373) !important;
        color: white !important;
        border-radius: 15px !important;
        padding: 15px !important;
        font-size: 16px !important;
    }
    
    .stWarning {
        background: linear-gradient(135deg, #FF9800, #FFB74D) !important;
        color: white !important;
        border-radius: 15px !important;
        padding: 15px !important;
        font-size: 16px !important;
    }
    
    /* Auto scroll to bottom */
    .chat-container {
        scroll-behavior: smooth;
    }
</style>
""", unsafe_allow_html=True)

# Initialize text-to-speech engine
def init_tts():
    if 'engine' not in st.session_state:
        st.session_state.engine = pyttsx3.init()
        # Set voice properties for friendlier sound
        voices = st.session_state.engine.getProperty('voices')
        if voices:
            # Try to set a female voice if available (usually more welcoming)
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    st.session_state.engine.setProperty('voice', voice.id)
                    break
        st.session_state.engine.setProperty('rate', 150)  # Slower speech rate

def speak(text):
    try:
        if 'engine' in st.session_state:
            st.session_state.engine.say(text)
            st.session_state.engine.runAndWait()
    except:
        pass  # Silent fail if TTS doesn't work

# Initialize TTS
init_tts()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "greeted" not in st.session_state:
    greeting = "Hello! I am your government scheme assistant. I can help you learn about various government schemes and programs."
    speak(greeting)
    st.session_state.greeted = True
    st.session_state.messages.append({
        "type": "bot",
        "content": "🙏 Hello! I am your government scheme assistant. I can help you learn about various government schemes and programs."
    })

# Header
st.markdown('<h1 class="main-header">🏠 Government Scheme Assistant</h1>', unsafe_allow_html=True)

# Create layout with main chat area and sidebar for questions
col1, col2 = st.columns([3, 1])

with col1:
    # Chat container
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="chat-container" id="chat-container">', unsafe_allow_html=True)
        
        # Display chat messages
        for message in st.session_state.messages:
            if message["type"] == "user":
                st.markdown(f'<div class="user-message">👤 {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bot-message">🤖 {message["content"]}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Input area at bottom
    st.markdown('<div class="input-area">', unsafe_allow_html=True)
    
    # Create two columns for text input and mic button
    input_col1, input_col2 = st.columns([3, 1])
    
    with input_col1:
        user_text = st.text_input("", placeholder="Type your question here...", key="text_input", label_visibility="collapsed")
    
    with input_col2:
        mic_button = st.button("🎙️ Speak", key="mic_btn", help="Click to speak your question")
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💡 Common Questions")
    st.markdown("Click on the questions below:")
    
    # Predefined questions
    questions = [
        "🏠 What is housing scheme?",
        "💰 Tell me about pension schemes",
        "🌾 Information on farmer schemes",
        "👩‍⚕️ What are health schemes?",
        "🎓 Education scheme benefits",
        "💼 Employment guarantee programs"
    ]
    
    for i, question in enumerate(questions):
        if st.button(question, key=f"q_{i}", help="Click on this question"):
            # Add question to chat
            st.session_state.messages.append({
                "type": "user",
                "content": question
            })
            
            # Generate response based on question
            if "housing" in question.lower():
                response = "The Pradhan Mantri Awas Yojana (PM Housing Scheme) provides affordable housing for economically weaker sections. You need Aadhaar card and income certificate to apply. Visit your nearest government office for more details."
            elif "pension" in question.lower():
                response = "Old Age Pension Scheme provides monthly pension after 60 years of age. The National Social Assistance Programme covers various pension schemes. Apply at your nearest Anganwadi center or Tehsil office."
            elif "farmer" in question.lower():
                response = "PM Kisan Scheme provides ₹6000 annually to eligible farmers. You need land documents and Aadhaar card. Also, Crop Insurance Scheme protects against crop losses. Visit your nearest agriculture office."
            elif "health" in question.lower():
                response = "Ayushman Bharat provides health insurance up to ₹5 lakh per family annually. Get your Golden Card made at nearby Anganwadi or government hospital. It covers hospitalization costs."
            elif "education" in question.lower():
                response = "Various education schemes like scholarships for girls, mid-day meal program, and free textbooks are available. Contact your school or education department for specific scheme details."
            else:
                response = "MGNREGA provides 100 days of guaranteed employment per household annually. Get your job card made at the Gram Panchayat office. Work includes rural infrastructure development."
            
            st.session_state.messages.append({
                "type": "bot",
                "content": response
            })
            
            # Speak the response
            speak(response)
            
            # Force rerun to update chat and scroll
            st.rerun()

# Handle microphone input
if mic_button:
    recognizer = sr.Recognizer()
    
    with st.spinner("Listening... Please speak"):
        try:
            with sr.Microphone() as source:
                speak("Yes, I'm listening")
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
            user_input = recognizer.recognize_google(audio)
            
            # Add user message to chat
            st.session_state.messages.append({
                "type": "user", 
                "content": user_input
            })
            
            # Simple response (you can expand this with actual scheme logic)
            response = f"You asked: '{user_input}'. I'm searching for information about this..."
            st.session_state.messages.append({
                "type": "bot",
                "content": response
            })
            
            speak(response)
            st.success(f"You said: {user_input}")
            st.rerun()
            
        except sr.UnknownValueError:
            error_msg = "Sorry, I couldn't understand that. Please try again."
            st.error(error_msg)
            speak(error_msg)
        except sr.RequestError:
            error_msg = "There's an internet connection issue. Please try again later."
            st.error(error_msg)
            speak(error_msg)
        except sr.WaitTimeoutError:
            error_msg = "No speech detected. Please try again."
            st.warning(error_msg)
            speak(error_msg)

# Handle text input
if user_text:
    # Add user message to chat
    st.session_state.messages.append({
        "type": "user",
        "content": user_text
    })
    
    # Simple response (expand with actual logic)
    response = f"You asked: '{user_text}'. I can provide information about this..."
    st.session_state.messages.append({
        "type": "bot",
        "content": response
    })
    
    speak(response)
    st.success(f"You asked: {user_text}")
    st.rerun()

# Auto-scroll to bottom JavaScript
st.markdown("""
<script>
function scrollToBottom() {
    var chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}
setTimeout(scrollToBottom, 100);
</script>
""", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #5D4037; padding: 10px; font-size: 16px;">'
    '💙 This service is completely free | Made to provide accurate information about government schemes'
    '</div>', 
    unsafe_allow_html=True
)