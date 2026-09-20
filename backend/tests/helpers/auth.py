import os
import json
import httpx
from typing import Optional, Dict

_TOKEN_CACHE: Optional[str] = None

def get_test_credentials() -> Dict[str, str]:
    """Load canonical test credentials from JSON file."""
    creds_path = os.path.join(os.path.dirname(__file__), '..', 'test_credentials.json')
    with open(creds_path, 'r') as f:
        return json.load(f)

def get_test_auth_token(base_url: str = "http://localhost:8000") -> str:
    """
    Get a valid authentication token for the canonical test user.
    Creates the user if it doesn't exist.
    Caches the token in memory for subsequent calls.
    """
    global _TOKEN_CACHE
    if _TOKEN_CACHE:
        return _TOKEN_CACHE

    creds = get_test_credentials()
    login_url = f"{base_url}/api/auth/login"
    register_url = f"{base_url}/api/auth/register"

    # Try login first
    login_data = {
        "email": creds["email"],
        "password": creds["password"]
    }
    
    with httpx.Client() as client:
        # Backend uses LoginRequest Pydantic model
        response = client.post(login_url, json=login_data)
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                _TOKEN_CACHE = token
                return token

        # If login failed, try to create the account
        print(f"Login failed (status {response.status_code}). Attempting to register canonical test user.")
        register_data = {
            "name": creds["name"],
            "email": creds["email"],
            "password": creds["password"]
        }
        reg_response = client.post(register_url, json=register_data)
        
        if reg_response.status_code not in (200, 201):
            if "already registered" not in reg_response.text.lower():
                raise Exception(f"Failed to create test user: {reg_response.text}")

        # Try login again
        response = client.post(login_url, json=login_data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                _TOKEN_CACHE = token
                return token
                
        raise Exception(f"Failed to authenticate test user even after registration. Status: {response.status_code}, {response.text}")

if __name__ == "__main__":
    # Test script: force create/login the user
    try:
        token = get_test_auth_token()
        print("Successfully obtained authentication token for canonical test user.")
    except Exception as e:
        print(f"Error: {e}")
