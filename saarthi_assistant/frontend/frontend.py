import streamlit as st
import pyttsx3
import speech_recognition as sr

# --- CUSTOM CSS for pastel background and header fixes ---
st.markdown("""
<style>
/* Global pastel background */
.appview-container, .main, body, html {
    background: linear-gradient(135deg, #FFF6F9 0%, #DDF6F3 100%) !important;
    min-height: 100vh !important;
}
/* Header hut/icon fix and top spacing */
.main-header {
    margin-top: 0px !important;
    margin-bottom: 14px !important;
    padding-top: 26px !important;
    display: flex; 
    align-items: center;
    font-size: 2.6rem;
}
.main-header img, .main-header svg, .main-header .emoji {
    height: 40px !important;
    width: 40px !important;
    margin-right: 12px !important;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    vertical-align: middle !important;
}
.block-container {
    padding-top: 1rem !important;
}
.main-content {
    min-height: unset !important;
    padding-top: 0px !important;
}
.chat-wrapper {
    min-height: 100px !important;
    margin-top: 0px !important;
}
.messages-container {
    max-height: 53vh !important;
    min-height: 70px !important;
    overflow-y: auto !important;
    padding: 0px 0 8px 0 !important;
    background: none !important;
    scroll-behavior: smooth;
}
.user-message {
    background: linear-gradient(135deg, #B5EAD7, #C7CEDB);
    color: #2E3B42;
    padding: 14px 20px;
    border-radius: 20px 20px 7px 20px;
    margin: 10px 0 10px auto;
    max-width: 80%;
    font-size: 16px;
    box-shadow: 0 2px 15px rgba(181, 234, 215, 0.17);
    animation: slideInRight 0.3s ease;
}
.bot-message {
    background: linear-gradient(135deg, #FFB3BA, #FFDFBA);
    color: #5D4037;
    padding: 14px 20px;
    border-radius: 20px 20px 20px 7px;
    margin: 10px auto 10px 0;
    max-width: 80%;
    font-size: 16px;
    box-shadow: 0 2px 15px rgba(255, 179, 186, 0.17);
    animation: slideInLeft 0.3s ease;
}
@keyframes slideInRight {
    from {transform: translateX(40px); opacity:0;}
    to {transform: translateX(0); opacity:1;}
}
@keyframes slideInLeft {
    from {transform: translateX(-40px); opacity:0;}
    to {transform: translateX(0); opacity:1;}
}
.question-bubbles-container {
    margin-bottom: 8px !important;
    padding: 5px 0 10px 0 !important;
    gap: 8px !important;
}
.input-area {
    background: rgba(255,255,255,.97) !important;
    border-radius: 17px !important;
    padding: 10px 0 8px 0 !important;
    margin-top: 4px !important;
}
.stButton > button {
    background: linear-gradient(135deg, #FFB3DE, #FFCCCB) !important;
    color: #5D4037 !important;
    border-radius: 20px !important;
    padding: 10px 15px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    min-width: 130px !important;
    box-shadow: 0 4px 15px rgba(255, 179, 222, 0.25) !important;
    margin-right: 4px !important;
}
</style>
""", unsafe_allow_html=True)

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
    greeting = ("Hello! I am your government scheme assistant. "
                "I can help you learn about various government schemes and programs.")
    st.session_state.greeted = True
    st.session_state.messages.append({"type": "bot", "content": greeting})
    st.session_state.pending_tts = greeting
if "is_typing" not in st.session_state:
    st.session_state.is_typing = False

# --- HEADER ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)
st.markdown(
    '<h1 class="main-header">'
    '<span class="emoji" style="font-size:48px; margin-right:10px; vertical-align:middle;">🏠</span> '
    'Government Scheme Assistant'
    '</h1>', unsafe_allow_html=True,
)

# --- Question Bubbles ---
st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)
st.markdown('<div class="question-bubbles-container">', unsafe_allow_html=True)

questions = [
    "🏠 Housing Scheme",
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

# --- Input area with mic button only ---
st.markdown('<div class="input-area">', unsafe_allow_html=True)
_, input_col2 = st.columns([3,1])
with input_col2:
    mic_button = st.button("🎙 Speak", key="mic_btn", help="Click to speak your question")
st.markdown('</div>', unsafe_allow_html=True)

if mic_button:
    recognizer = sr.Recognizer()
    with st.spinner("Listening... Please speak"):
        try:
            with sr.Microphone() as source:
                speak("Yes, I'm listening.")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print(type(audio))  # Debugging line to check audio type
            user_input = recognizer.recognize_google(audio)
            st.session_state.messages.append({"type": "user", "content": user_input})
            standard_reply = "Thank you for your question. I am processing your request and will get back to you shortly."
            st.session_state.messages.append({"type": "bot", "content": standard_reply})
            st.success(f"You said: {user_input}")
            st.session_state.pending_tts = standard_reply
        except sr.UnknownValueError:
            error_msg = "Sorry, I couldn't understand that. Please try again."
            st.error(error_msg)
            st.session_state.pending_tts = error_msg
        except sr.RequestError:
            error_msg = "There's an internet connection issue. Please try again later."
            st.error(error_msg)
            st.session_state.pending_tts = error_msg
        except sr.WaitTimeoutError:
            error_msg = "No speech detected. Please try again."
            st.warning(error_msg)
            st.session_state.pending_tts = error_msg

# --- AFTER ALL UI, run TTS if pending ---
if 'pending_tts' in st.session_state:
    speak(st.session_state['pending_tts'])
    del st.session_state['pending_tts']

# --- Footer ---
st.markdown("---", unsafe_allow_html=True)
st.markdown(
    '<div style="text-align: center; color: #5D4037; padding: 5px; font-size: 15px;">'
    '💙 This service is completely free | Made to provide accurate information about government schemes'
    '</div>',
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)