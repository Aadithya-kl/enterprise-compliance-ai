"""
Verification script for the admin bootstrap and login flow.
"""
import sys
import time
import requests
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def clear_existing_admins():
    print("Step 1: Clearing existing admin users from database to ensure clean seeding...")
    db = SessionLocal()
    try:
        admins = db.query(User).filter(
            (User.role == UserRole.ADMIN) | (User.email == "admin@company.com")
        ).all()
        for u in admins:
            db.delete(u)
        db.commit()
        print(f"Successfully deleted {len(admins)} admin user(s).")
    except Exception as e:
        db.rollback()
        print("Error clearing admins:", e)
        sys.exit(1)
    finally:
        db.close()


def verify_admin_in_db():
    print("\nStep 2: Checking database for seeded admin user...")
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@company.com").first()
        if not admin:
            print("FAILED: Seeded admin user 'admin@company.com' not found in database.")
            sys.exit(1)
        
        print(f"SUCCESS: Found user 'admin@company.com'")
        print(f"  - Full Name: {admin.full_name}")
        print(f"  - Role: {admin.role.value if hasattr(admin.role, 'value') else admin.role}")
        print(f"  - Is Active: {admin.is_active}")
        
        # Verify fields match exactly
        assert admin.full_name == "System Administrator", "full_name does not match"
        role_str = admin.role.value if hasattr(admin.role, "value") else admin.role
        assert role_str == "admin", "role does not match"
        assert admin.is_active is True, "user is not active"
        print("Database field assertions PASSED.")
    except Exception as e:
        print("FAILED verification inside database:", e)
        sys.exit(1)
    finally:
        db.close()


def verify_login():
    print("\nStep 3: Verifying login API endpoint via POST /api/v1/auth/login...")
    url = "http://localhost:8000/api/v1/auth/login"
    payload = {
        "email": "admin@company.com",
        "password": "Admin123!"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Response status code: {response.status_code}")
        if response.status_code != 200:
            print(f"FAILED: Login request failed with status code {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        data = response.json()
        print("Login SUCCESS. Received token response:")
        print(f"  - token_type: {data.get('token_type')}")
        print(f"  - expires_in: {data.get('expires_in')} seconds")
        print(f"  - access_token (truncated): {data.get('access_token')[:20]}...")
        
        assert "access_token" in data, "access_token is missing"
        assert "refresh_token" in data, "refresh_token is missing"
        assert data.get("token_type") == "bearer", "token_type is not bearer"
        print("API field assertions PASSED.")
    except Exception as e:
        print("FAILED API login check:", e)
        sys.exit(1)


def verify_invalid_login():
    print("\nStep 4: Verifying invalid login attempt is rejected...")
    url = "http://localhost:8000/api/v1/auth/login"
    payload = {
        "email": "admin@company.com",
        "password": "WrongPassword123!"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Response status code: {response.status_code}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Invalid login rejected with 401 Unauthorized.")
    except Exception as e:
        print("FAILED invalid login check:", e)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_existing_admins()
    elif len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_admin_in_db()
        verify_login()
        verify_invalid_login()
        print("\n" + "="*50)
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY")
        print("="*50)
    else:
        print("Usage: python verify_bootstrap.py [--clear | --verify]")
