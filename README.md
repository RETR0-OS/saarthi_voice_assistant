# Saarthi – AI Voice Assistant for Government Schemes

Saarthi is an AI-powered, voice-first assistant that helps citizens discover, understand, and act on government schemes. It combines speech input/output, face-based authentication, and secure handling of personal identifiable information (PII) to deliver a guided, multilingual experience through a simple web interface.

## Mission

- Make government schemes accessible, understandable, and actionable to everyone
- Provide a voice-first, low-friction interface for discovery and Q&A
- Protect user privacy and PII with encryption and secure session design
- Support inclusive UX with Hindi/English prompts and TTS responses

## Key Features

- Voice interaction
  - Record speech, transcribe to text, and play back responses via TTS[1]
- Face authentication and registration
  - Face-based login with fallback to guided registration and PII setup[2][1]
- Secure PII flow
  - Encrypted storage and controlled access to Aadhaar, PAN, and other PII via tools guarded by authentication and session checks[2]
- Agentic workflow and memory
  - LangGraph-powered state machine with checkpoints, routing, and message trimming[2]
- Streamlit UI
  - Clean, centered app with guided flows for auth, registration, and agent chat[1]
- Example form
  - test_form.html for local testing of form filling and PII-related fields[3]

## Architecture Overview

### Frontend UI: Streamlit app (frontend.py)
  - Authentication screen with face login, registration form, PII collection, and agent chat UI[1]
  - Audio recording (sounddevice + numpy) and TTS (pyttsx3)
  - Invokes voice service for transcription via saarthi_assistant.voice.main.transcribe_audio_numpy[1]
  - Integrates with sub-graph runner API: run_authentication, submit_registration_data, submit_pii_data, start_agent_conversation, send_agent_message, end_agent_conversation[1]

### Orchestration/Agent Graph: LangGraph (basic_graph.py)
  - StateGraph with clear workflow phases: initialization, authentication, registration, PII setup, query processing, completion[2]
  - Checkpointing and encrypted serialization (SqliteSaver + EncryptedSerializer) for short-term memory[2]
  - Tooling layer guarded by AuthenticationStatus and session checks:
    - fetch_user_pii: retrieves decrypted PII into session cache only when authenticated and session-active
    - fill_secure_form: fills forms with PII using cache or secure fetch after re-authentication[2]
  - Uses local/edge LLM (ChatOllama with qwen3:4b) for reasoning and fast responses[2]

### Identity and PII
  - IdentityManager (in saarthi_assistant.identity_wallet.identity_manager.*) handles login (face auth), verify_user, add_user, encrypt_pii_data, decrypt_pii_data[2]
  - PII cache scoped to session and cleared on logout[2]

### Core Package: saarthi_assistant
  - identity_wallet/: identity and PII management
  - voice/: audio capture/transcription utilities
  - prompt_store/: prompts for agents/managers
  - sub_graphs/: graph runner and workflow helpers
  - utilities/: common helpers[4][1][2]

### Example Assets and Docs: extras/
  - Hackathon presentation, problem statement, useful references

## Directory Structure

- saarthi_assistant/
  - identity_wallet/
  - prompt_store/
  - sub_graphs/
    - graph_runner.py (referenced from frontend.py)
  - utilities/
  - voice/
  - __init__.py[4][1]

- basic_graph.py
  - LangGraph state machine and tools[2]

- frontend.py
  - Streamlit UI and end-to-end user flow[1]

- test_form.html
  - Example form (Aadhaar, PAN, etc.) for testing[3]

- extras/
  - Hackatone_presentation.pptx, README.md, problem_statement.md, useful_stuff.md (placeholders)[5]

- pyproject.toml
  - Project metadata and high-level dependencies (Python >=3.11,=3.11,<3.12[6]
- Camera index: set via CAMERA_IDX in .env or adapt calls to IdentityManager [page/code]
- Model/runtime:
  - ChatOllama uses qwen3:4b in both reasoning and fast modes[2]
  - Ensure Ollama is running locally and qwen3:4b is available, or refactor to your preferred LLM backend

## Troubleshooting

- Microphone not detected
  - Check OS microphone permissions; verify sounddevice works with python -c "import sounddevice as sd; print(sd.query_devices())"
- No speech detected
  - The UI warns when input amplitude is too low; speak closer to the mic or increase volume[1]
- Camera not found
  - Adjust CAMERA_IDX; verify your camera index with other tools; ensure permissions
- Authentication fails repeatedly
  - The graph caps retries; after failures it routes to error handling or registration. Check lighting and camera quality[2]
- PII retrieval or form filling fails
  - Ensure active session and authenticated status; tools explicitly reject operations if unauthenticated or session inactive[2]
- Streamlit not launching
  - Verify Python 3.11, reinstall dependencies, check port conflicts (set STREAMLIT_SERVER_PORT)
- Ollama/LLM errors
  - Ensure Ollama is running and the model qwen3:4b is installed; or switch to a supported provider based on your environment[2]

## Roadmap

- Multilingual assistant responses (Hindi TTS, bilingual UI)
- Scheme discovery with retrieval over authoritative sources
- Form automation for official portals (browser automation with strict security boundaries)
- Offline/low-connectivity modes
- Mobile-friendly PWA packaging
- Better observability and consent-driven analytics

## Contributing

Contributions are welcome! Please:
- Open an issue describing the change
- Follow the security patterns for PII access and session checks
- Keep UI changes accessible and simple
- Add tests where feasible

## License

- Distributed under the License settings defined in the `License.md`

## Acknowledgements

- LangGraph and LangChain ecosystems for agent orchestration[7][6][2]
- Streamlit for rapid UI development[1]
- Open-source face recognition and CV libraries used in identity flows[7]
- The contributors and community supporting this project

## Appendix: Example Commands

- Install and run (pip):
  - python3.11 -m venv .venv && source .venv/bin/activate
  - pip install -r requirements.txt
  - streamlit run frontend.py
- Run with uv:
  - uv sync
  - uv run streamlit run frontend.py

## Notes on Data and Compliance

- PII usage should be minimized. Ensure the collection and processing align with legal bases appropriate to your jurisdiction.
- Provide user consent, data deletion mechanisms, and transparent notices in production.
- Consider external secrets management for encryption keys and avoid storing secrets in .env in production.
