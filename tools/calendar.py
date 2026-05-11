import logging
import datetime
from tools.google_api import get_calendar_service

logger = logging.getLogger("SPARK_CALENDAR")

def get_upcoming_events(max_results=3):
    """Fetches upcoming Google Calendar events."""
    service = get_calendar_service()
    if not service:
        return []
        
    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        return []

def format_upcoming_events_for_speech(events):
    """Formats event data into a spoken summary."""
    if not events:
        return ""
        
    lines = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        # Parse ISO format for speech
        try:
            dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
            time_str = dt.strftime("%I:%M %p")
            lines.append(f"{event['summary']} at {time_str}")
        except:
            lines.append(event['summary'])
            
    summary = ", and ".join(lines)
    return f"You have upcoming events: {summary}."
