import streamlit as st
import pyttsx3
import speech_recognition as sr
import os

# Initialize text-to-speech engine
engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

# Say hello when app loads
if "greeted" not in st.session_state:
    speak("Hello! I am your scheme assistant.")
    st.session_state.greeted = True

st.title("🎤 Voice Assistant for Schemes")

st.write("Click the mic button below and speak a question.")

# Microphone input
if st.button("🎙️ Speak Now"):
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        speak("Listening...")
        try:
            audio = recognizer.listen(source, timeout=5)
            user_input = recognizer.recognize_google(audio)
            st.success(f"You said: {user_input}")
            speak(f"You said {user_input}")
        except sr.UnknownValueError:
            st.error("Sorry, I could not understand that.")
            speak("Sorry, I could not understand that.")
        except sr.RequestError:
            st.error("Could not request results from Google Speech Recognition service.")
            speak("Speech recognition service is not working right now.")
        except sr.WaitTimeoutError:
            st.warning("No speech detected. Please try again.")
            speak("No speech detected.")
