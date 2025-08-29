#!/usr/bin/env python3
"""
Simple OAuth setup for Google Calendar, Gmail, and Google Docs.
Gets refresh token and saves to .env file.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
import dotenv

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.readonly'
]

def setup_oauth():
    dotenv.load_dotenv()
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not found in .env file")
        return
    
    CLIENT_CONFIG = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    print("🔐 Starting OAuth flow...")
    print("This will open a browser for Google authentication.")
    
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0)
    
    print(f"✅ OAuth complete!")
    print(f"🔑 Refresh token: {creds.refresh_token}")
    
    # Update .env file with new refresh token
    dotenv_path = '.env'
    with open(dotenv_path, 'r') as f:
        lines = f.readlines()
    
    # Remove old refresh token line if exists
    lines = [line for line in lines if not line.startswith('GOOGLE_REFRESH_TOKEN=')]
    
    # Add new refresh token
    lines.append(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}\n")
    
    with open(dotenv_path, 'w') as f:
        f.writelines(lines)
    
    print("📝 Refresh token updated in .env file")

if __name__ == "__main__":
    setup_oauth()
