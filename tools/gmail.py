import logging
import base64
from email.message import EmailMessage
from tools.google_api import get_gmail_service

logger = logging.getLogger("SPARK_GMAIL")

def read_unread_emails(max_results=5):
    """Fetches unread emails from Gmail."""
    service = get_gmail_service()
    if not service:
        return "Gmail integration is not configured. Please add credentials.json."
        
    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "You have no new unread emails, sir."
            
        email_summaries = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From']).execute()
            headers = msg_data.get('payload', {}).get('headers', [])
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
            sender = next((header['value'] for header in headers if header['name'] == 'From'), "Unknown Sender")
            email_summaries.append(f"From {sender}: {subject}")
            
        summary = "\n".join(email_summaries)
        return f"You have {len(messages)} new emails:\n{summary}"
        
    except Exception as e:
        logger.error(f"Gmail read error: {e}")
        return "I encountered an error reading your emails."

def send_email(to: str, subject: str, body: str):
    """Sends an email via Gmail."""
    service = get_gmail_service()
    if not service:
        return "Gmail integration is not configured."
        
    try:
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['Subject'] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        service.users().messages().send(userId="me", body=create_message).execute()
        return f"Email successfully sent to {to}."
    except Exception as e:
        logger.error(f"Gmail send error: {e}")
        return "I encountered an error sending the email."
