# Models
- **Multilingual Indian speech-to-text**: [HF](https://huggingface.co/ai4bharat/indic-seamless)
- **Reasoning Model**: [Ollama](https://ollama.com/library/qwen3)
- **Translation to local languages**: GPT-4o-mini
- **Text-to-Speech**: Google TTS

# Framework
- **CrewAI**
- **Hugging Face**
- **Ollama**

# Tools
- **Tavily Search API**
- **DuckDuckGo Search API**
- **Selenium**

```python
# Initialize the identity manager
identity_mgr = IdentityManager()

# Enroll a new user
result = identity_mgr.add_user("John Doe")

# Encrypt PII data
identity_mgr.encrypt_pii_data("ssn", "123-45-6789")
identity_mgr.encrypt_pii_data("credit_card", "4532-1234-5678-9012")

# Logout (wipes memory)
identity_mgr.logout()

# Login again with face
login_result = identity_mgr.login()

# Decrypt PII data
ssn_data = identity_mgr.decrypt_pii_data("ssn")
```