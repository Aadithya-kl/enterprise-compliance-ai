import requests

def test_register():
    # Login as admin
    login_url = "http://localhost:8000/api/v1/auth/login"
    login_payload = {
        "email": "admin@company.com",
        "password": "Admin123!"
    }
    
    response = requests.post(login_url, json=login_payload)
    if response.status_code != 200:
        print("Login failed:", response.text)
        return
        
    token = response.json()["access_token"]
    print("Logged in as admin. Token received.")
    
    # Try to register a user
    register_url = "http://localhost:8000/api/v1/auth/register"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    register_payload = {
        "email": "testuser_unique@company.com",
        "full_name": "Test User Unique",
        "password": "UserPassword123!",
        "role": "auditor"
    }
    
    print("Sending registration request...")
    response = requests.post(register_url, json=register_payload, headers=headers)
    print("Response status:", response.status_code)
    print("Response text:", response.text)

if __name__ == "__main__":
    test_register()
