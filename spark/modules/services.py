from core.vault import spark_vault
import time

class ServiceAssistant:
    def __init__(self):
        self.name = "Executive Assistant"

    def get_calendar_events(self, count=3):
        """
        Retrieves the next N events from the calendar.
        Requires 'google_calendar_token' in the Vault.
        """
        token = spark_vault.get_secret("google_calendar_token")
        if not token:
            print("[SERVICES] Error: Google Calendar token not found in Vault.")
            return "I don't have access to your calendar yet. Please add your token to my Vault."
        
        print(f"[SERVICES] Authenticating with Vault token for Calendar...")
        # Placeholder for actual Google API call logic
        # In Phase 5, this would use google-api-python-client
        time.sleep(1) 
        
        mock_events = [
            {"summary": "S.P.A.R.K. Phase 5 Review", "start": "2026-02-15T10:00:00Z"},
            {"summary": "Lunch with Stark", "start": "2026-02-15T12:30:00Z"},
            {"summary": "Global Network Deployment", "start": "2026-02-16T09:00:00Z"}
        ]
        
        events_str = "\n".join([f"- {e['summary']} at {e['start']}" for e in mock_events[:count]])
        return f"Here are your next {count} events:\n{events_str}"

    def draft_email(self, recipient, subject, body):
        """
        Drafts an email. Permissive access.
        """
        print(f"[SERVICES] Drafting email to {recipient}...")
        # Placeholder for Gmail API draft creation
        return f"DRAFT CREATED: To: {recipient}, Subject: {subject}\nBody: {body}\nShould I send this?"

    def send_email(self, draft_id):
        """
        Sends a drafted email. Sensitive action (requires permission).
        """
        # This would be called AFTER the user confirms via the Human Firewall
        print(f"[SERVICES] Sending email draft {draft_id}...")
        return "Email sent successfully."

# Global instance
service_assistant = ServiceAssistant()

if __name__ == "__main__":
    # Secretary Test
    print("--- Running Secretary Test ---")
    # Simulate adding token to vault first
    spark_vault.set_secret("google_calendar_token", "ya29.mock_google_token")
    
    assistant = ServiceAssistant()
    schedule = assistant.get_calendar_events(2)
    print(schedule)
    
    draft = assistant.draft_email("boss@example.com", "Progress Report", "S.P.A.R.K. is now connected.")
    print(f"\n{draft}")
    
    # Cleanup for clean state
    # spark_vault.set_secret("google_calendar_token", None) 
