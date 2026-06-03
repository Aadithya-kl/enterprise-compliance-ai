import requests
import sys

def verify_user_management():
    # 1. Login as Admin
    print("Step 1: Authenticating as Admin...")
    login_url = "http://localhost:8000/api/v1/auth/login"
    login_payload = {
        "email": "admin@company.com",
        "password": "Admin123!"
    }
    
    response = requests.post(login_url, json=login_payload)
    if response.status_code != 200:
        print("FAILED: Admin login failed:", response.text)
        sys.exit(1)
        
    token = response.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    print("SUCCESS: Admin logged in.")

    # 2. Create User
    print("\nStep 2: Creating a new user via POST /api/v1/auth/register...")
    register_url = "http://localhost:8000/api/v1/auth/register"
    register_payload = {
        "email": "audit_test_user@company.com",
        "full_name": "Audit Test User Initial",
        "password": "AuditPassword123!",
        "role": "auditor"
    }
    
    response = requests.post(register_url, json=register_payload, headers=headers)
    if response.status_code != 201:
        print("FAILED: User registration failed:", response.text)
        sys.exit(1)
        
    user_data = response.json()
    user_id = user_data["id"]
    print(f"SUCCESS: User created with ID {user_id}")
    assert user_data["email"] == "audit_test_user@company.com"
    assert user_data["full_name"] == "Audit Test User Initial"
    assert user_data["role"] == "auditor"
    assert user_data["is_active"] is True

    # 3. Verify user appears in user list
    print("\nStep 3: Verifying user appears in list via GET /api/v1/users...")
    list_url = "http://localhost:8000/api/v1/users"
    response = requests.get(list_url, headers=headers)
    if response.status_code != 200:
        print("FAILED: Fetching user list failed:", response.text)
        sys.exit(1)
        
    list_data = response.json()
    found = False
    for u in list_data["users"]:
        if u["id"] == user_id:
            found = True
            break
    assert found, "Created user not found in the user list"
    print("SUCCESS: User exists in user list.")

    # 4. Edit User (Role & Full Name)
    print("\nStep 4: Editing user via PATCH /api/v1/users/{id}...")
    update_url = f"http://localhost:8000/api/v1/users/{user_id}"
    update_payload = {
        "full_name": "Audit Test User Edited",
        "role": "compliance_officer"
    }
    
    response = requests.patch(update_url, json=update_payload, headers=headers)
    if response.status_code != 200:
        print("FAILED: Editing user failed:", response.text)
        sys.exit(1)
        
    updated_data = response.json()
    print("SUCCESS: User updated successfully.")
    assert updated_data["full_name"] == "Audit Test User Edited"
    assert updated_data["role"] == "compliance_officer"
    print("  - Updated Full Name:", updated_data["full_name"])
    print("  - Updated Role:", updated_data["role"])

    # 5. Delete (Deactivate) User
    print("\nStep 5: Deactivating user via DELETE /api/v1/users/{id}...")
    delete_url = f"http://localhost:8000/api/v1/users/{user_id}"
    response = requests.delete(delete_url, headers=headers)
    if response.status_code != 204:
        print("FAILED: Deactivating user failed:", response.text)
        sys.exit(1)
    print("SUCCESS: Deactivation API request completed with 204 No Content.")

    # 6. Verify user status is now Inactive
    print("\nStep 6: Verifying user status is inactive in user list...")
    response = requests.get(list_url, headers=headers)
    list_data = response.json()
    user_in_list = None
    for u in list_data["users"]:
        if u["id"] == user_id:
            user_in_list = u
            break
            
    assert user_in_list is not None, "User disappeared from list"
    assert user_in_list["is_active"] is False, "User is still active"
    print("SUCCESS: Verified user 'is_active' status is False (Deactivated).")

    # 7. Cleanup test user from database
    print("\nStep 7: Cleaning up test user from database...")
    from app.db.session import SessionLocal
    from app.models.user import User
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            db.delete(u)
            db.commit()
            print("SUCCESS: Cleaned up test user.")
    except Exception as e:
        db.rollback()
        print("Error clearing test user from DB:", e)
    finally:
        db.close()

if __name__ == "__main__":
    verify_user_management()
    print("\n" + "="*50)
    print("ALL USER MANAGEMENT ENDPOINTS VERIFIED SUCCESSFULLY")
    print("="*50)
