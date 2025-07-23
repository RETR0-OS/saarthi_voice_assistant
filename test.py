import time

from identity_wallet.identity_manager.identity_manager import IdentityManager

id_manager = IdentityManager(camera_id=1)

print("Adding user...")
# time.sleep(2)
print(id_manager.add_user(first_name="Aaditya", last_name="Jindal", dob="2000-01-01", phone=1234567890))

print("Encrypting PII data...")
id_manager.encrypt_pii_data("adhaar_no", "1234-5678-9012")
id_manager.encrypt_pii_data("pan_no", "1234567890")

id_manager.logout()

print("Encryption complete. Press enter to continue...")

input()

login_result = id_manager.login()

print(login_result)

# Decrypt PII data
ssn_data = id_manager.decrypt_pii_data("adhaar_no")

print(f"Decrypted Aadhaar No: {ssn_data}")