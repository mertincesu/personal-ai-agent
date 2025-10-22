"""
Centralized Google OAuth authentication for Calendar and Gmail
Uses only 3 environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
"""

import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_google_credentials():
    """Get Google OAuth credentials from environment variables"""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") 
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Missing OAuth credentials. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN in .env")
    
    return Credentials(
        None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
    )

def get_calendar_service():
    """Get Google Calendar service"""
    creds = get_google_credentials()
    return build("calendar", "v3", credentials=creds)

def get_gmail_service():
    """Get Gmail service"""
    creds = get_google_credentials()
    return build("gmail", "v1", credentials=creds)

def get_docs_service():
    """Get Google Docs service"""
    creds = get_google_credentials()
    return build("docs", "v1", credentials=creds)

def get_drive_service():
    """Get Google Drive service"""
    creds = get_google_credentials()
    return build("drive", "v3", credentials=creds)
