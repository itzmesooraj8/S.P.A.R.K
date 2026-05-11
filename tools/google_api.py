import os
import pickle
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger("SPARK_GOOGLE_API")

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.readonly'
]

def get_google_credentials():
    """Authenticates with Google APIs using credentials.json."""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), '..', 'token.pickle')
    creds_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh Google token: {e}")
                creds = None
                
        if not creds:
            if not os.path.exists(creds_path):
                logger.warning("Google credentials.json not found. Integrations disabled.")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Google API Authentication failed: {e}")
                return None
                
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
            
    return creds

def get_gmail_service():
    creds = get_google_credentials()
    if not creds: return None
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)

def get_calendar_service():
    creds = get_google_credentials()
    if not creds: return None
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)
