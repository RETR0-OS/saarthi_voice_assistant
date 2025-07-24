# Identity Management Tools Guide

This guide explains how to use the secure identity management tools that allow agents to authenticate users and work with PII (Personally Identifiable Information) without ever accessing or viewing the actual personal data.

## Overview

The identity management system provides the following key capabilities:
- Face recognition-based authentication
- Secure PII storage and retrieval
- Privacy-preserving PII usage in forms/applications
- Complete isolation of personal data from AI agents
- **Optimized performance with singleton pattern**

## Performance Optimization

### Singleton Pattern Implementation

The Identity Manager uses a singleton pattern through the `IdentityManagerSingleton` wrapper class to optimize performance:

**Benefits:**
- **Reduced Overhead**: Only one IdentityManager instance is created across the entire application
- **Shared Resources**: Camera resources, database connections, and cryptographic keys are shared efficiently
- **Memory Optimization**: Prevents multiple heavy instances from consuming excessive memory
- **Thread Safety**: Uses threading locks to ensure safe concurrent access

**How it Works:**
```python
# All tools automatically use the same singleton instance
auth_tool = UserAuthenticationTool()
pii_tool = PIIRetrievalTool()

# Both tools share the same underlying IdentityManager instance
# No additional overhead for creating multiple instances
```

**Singleton Management:**
```python
# Get the singleton instance directly (if needed)
identity_manager = IdentityManagerSingleton.get_instance()

# Reset the singleton (useful for testing or cleanup)
IdentityManagerSingleton.reset_instance()
```

## Available Tools

### 1. UserAuthenticationTool
Manages user authentication through face recognition.

**Actions:**
- `login` - Authenticate user via face recognition
- `logout` - End user session and clear memory
- `verify` - Check if user is currently authenticated
- `status` - Get current login and session status

**Example Usage:**
```python
# Check authentication status
result = user_authentication_tool.run(action="status")
# Returns: {"success": true, "logged_in": false, "session_active": false, "message": "Login status: Inactive"}

# Login user
result = user_authentication_tool.run(action="login")
# Returns: {"success": true, "message": "User authenticated successfully", "session_active": true}
```

### 2. PIIRetrievalTool
Checks if specific PII data exists without revealing the actual data.

**Parameters:**
- `data_type` - Type of PII to check (e.g., "aadhaar", "pan", "phone", "address")

**Example Usage:**
```python
# Check if Aadhaar data exists
result = pii_retrieval_tool.run(data_type="aadhaar")
# Returns: {"success": true, "data_exists": true, "data_type": "aadhaar", "message": "PII data of type 'aadhaar' is available"}
```

### 3. PIIWriterTool
Uses PII data to fill forms without exposing it to the agent.

**Parameters:**
- `data_type` - Type of PII to use
- `target_field` - Field identifier where data should be entered
- `form_id` - Optional form identifier for tracking

**Example Usage:**
```python
# Fill Aadhaar number in a form field
result = pii_writer_tool.run(
    data_type="aadhaar",
    target_field="aadhaar_number_field",
    form_id="pm_kisan_form"
)
# Returns: {"success": true, "message": "PII data of type 'aadhaar' has been securely entered into field 'aadhaar_number_field'", "action_log": {...}}
```

### 4. PIIStorageTool
Requests PII data from user for secure storage.

**Parameters:**
- `data_type` - Type of PII to store
- `prompt_message` - Message explaining why the data is needed

**Example Usage:**
```python
# Request Aadhaar number from user
result = pii_storage_tool.run(
    data_type="aadhaar",
    prompt_message="Your Aadhaar number is required for government scheme verification"
)
# Returns: {"success": true, "message": "Request sent to user for 'aadhaar' data", "status": "awaiting_user_input"}
```

### 5. UserEnrollmentTool
Initiates new user enrollment with face biometrics.

**Parameters:**
- `enrollment_request` - Description of enrollment request

**Example Usage:**
```python
# Start enrollment
result = user_enrollment_tool.run(
    enrollment_request="Enroll new user for government services access"
)
# Returns: {"success": true, "message": "User enrollment process initiated", "status": "awaiting_user_data"}
```

## Security Features

### Privacy Protection
- **No PII Exposure**: Agents never see actual personal data
- **Face Authentication**: Users authenticated via face recognition before any PII access
- **Re-authentication**: Critical operations require fresh face verification
- **Encrypted Storage**: All PII data is encrypted at rest

### Performance Security
- **Singleton Pattern**: Prevents resource exhaustion attacks through excessive instance creation
- **Thread Safety**: Concurrent access is safely managed with locks
- **Memory Protection**: Efficient memory usage prevents information leakage through memory exhaustion

### Data Flow
1. User authenticates with face → Identity Manager verifies
2. Agent requests PII check → Tool confirms existence without revealing data
3. Agent requests form filling → Tool retrieves and uses PII securely
4. User sees confirmation → Agent only sees success/failure status

## Best Practices

### 1. Always Authenticate First
```python
# Good practice
auth_status = user_authentication_tool.run(action="verify")
if auth_status["authenticated"]:
    # Proceed with PII operations
else:
    # Request login first
```

### 2. Check Data Availability Before Use
```python
# Check if required data exists
check_result = pii_retrieval_tool.run(data_type="aadhaar")
if check_result["data_exists"]:
    # Use the data
    write_result = pii_writer_tool.run(data_type="aadhaar", target_field="id_field")
```

### 3. Provide Clear Context for Data Requests
```python
# Good - explains why data is needed
storage_result = pii_storage_tool.run(
    data_type="pan",
    prompt_message="PAN card details needed for income tax benefit claims under this scheme"
)
```

### 4. Handle Failures Gracefully
```python
result = user_authentication_tool.run(action="login")
if not result["success"]:
    # Handle authentication failure
    print(f"Authentication failed: {result['message']}")
```

### 5. Efficient Resource Usage
```python
# Good - Multiple tools share the same IdentityManager instance
auth_tool = UserAuthenticationTool()
pii_tool = PIIRetrievalTool()
writer_tool = PIIWriterTool()

# All tools automatically use the singleton instance
# No need to manually manage instance creation
```

## Integration Examples

### Example 1: Government Scheme Application
```python
# 1. Authenticate user
auth_result = user_authentication_tool.run(action="login")

# 2. Check required documents
for doc_type in ["aadhaar", "pan", "address"]:
    check_result = pii_retrieval_tool.run(data_type=doc_type)
    if not check_result["data_exists"]:
        # Request missing document
        storage_result = pii_storage_tool.run(
            data_type=doc_type,
            prompt_message=f"{doc_type} required for scheme application"
        )

# 3. Fill application form
field_mappings = {
    "aadhaar": "aadhaar_field",
    "pan": "pan_field",
    "address": "address_field"
}

for data_type, field_name in field_mappings.items():
    write_result = pii_writer_tool.run(
        data_type=data_type,
        target_field=field_name,
        form_id="scheme_application"
    )
```

### Example 2: Secure Document Verification
```python
# 1. Verify user identity
auth_result = user_authentication_tool.run(action="login")

# 2. Check if verification documents exist
docs_to_verify = ["aadhaar", "pan"]
available_docs = []

for doc in docs_to_verify:
    check_result = pii_retrieval_tool.run(data_type=doc)
    if check_result["data_exists"]:
        available_docs.append(doc)

# 3. Use documents for verification without seeing them
for doc in available_docs:
    verify_result = pii_writer_tool.run(
        data_type=doc,
        target_field=f"verify_{doc}_field",
        form_id="kyc_verification"
    )
```

## Important Notes

1. **Session Management**: User sessions are temporary. Keys are wiped from memory on logout or system close.
2. **Hardware Security**: Wrapping keys are stored in hardware-backed secure storage when available.
3. **No Manual Override**: There is no way for agents to bypass privacy protections and access raw PII.
4. **Audit Trail**: All PII usage is logged for security auditing (without exposing the data itself).
5. **Performance Optimization**: Singleton pattern ensures efficient resource usage across the application.

## Advanced Usage

### Singleton Instance Management

```python
# Get direct access to the singleton (if needed for advanced operations)
from crew.tools import IdentityManagerSingleton

# Get the singleton instance
identity_manager = IdentityManagerSingleton.get_instance()

# Check if instance is initialized
if IdentityManagerSingleton._instance is not None:
    print("IdentityManager singleton is active")

# Reset singleton for testing or cleanup
IdentityManagerSingleton.reset_instance()
```

### Thread Safety Considerations

```python
# The singleton is thread-safe and can be used in concurrent scenarios
import threading

def worker_function():
    auth_tool = UserAuthenticationTool()
    # Each thread safely accesses the same singleton instance
    result = auth_tool.run(action="status")

# Multiple threads can safely use the tools
threads = []
for i in range(5):
    thread = threading.Thread(target=worker_function)
    threads.append(thread)
    thread.start()
```

## Troubleshooting

### Common Issues:

1. **"User not authenticated"**
   - Solution: Ensure user has logged in with `user_authentication_tool.run(action="login")`

2. **"PII data not found"**
   - Solution: Check if data exists first, then request storage if needed

3. **"Re-authentication failed"**
   - Solution: User's face must match the enrolled biometric. Ensure good lighting and camera angle.

4. **"Failed to retrieve secure key"**
   - Solution: User may need to re-enroll if secure storage was corrupted.

5. **Performance Issues**
   - Solution: The singleton pattern should prevent most performance issues. If problems persist, check for resource leaks or consider calling `IdentityManagerSingleton.reset_instance()` to start fresh. 