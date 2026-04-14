import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")
SLOT_START_HOUR = 12
SLOT_END_HOUR = 15
SLOT_DURATION_MINUTES = 30
MEETING_BUFFER_MINUTES = 15
LOOKAHEAD_DAYS = 14


def _get_calendar_service():
    """Build Google Calendar API service using OAuth 2.0 refresh token."""
    refresh_token = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN", "")
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    if not all([refresh_token, client_id, client_secret]):
        return None

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_available_slots(num_slots: int = 3) -> List[Dict[str, str]]:
    """Return up to `num_slots` free 30-min slots in the 12-15 ET window over the next N weekdays."""
    service = _get_calendar_service()
    if not service:
        return []

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    now = datetime.now(ET)
    slots: List[Dict[str, str]] = []

    for day_offset in range(1, LOOKAHEAD_DAYS + 1):
        candidate_day = now + timedelta(days=day_offset)
        if candidate_day.weekday() >= 5:
            continue

        window_start = candidate_day.replace(
            hour=SLOT_START_HOUR, minute=0, second=0, microsecond=0
        )
        window_end = candidate_day.replace(
            hour=SLOT_END_HOUR, minute=0, second=0, microsecond=0
        )

        body = {
            "timeMin": window_start.isoformat(),
            "timeMax": window_end.isoformat(),
            "timeZone": "America/New_York",
            "items": [{"id": calendar_id}],
        }
        try:
            result = service.freebusy().query(body=body).execute()
        except Exception as e:
            print(f"Google Calendar freebusy error: {e}")
            continue

        busy_periods = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])

        slot_start = window_start
        while slot_start + timedelta(minutes=SLOT_DURATION_MINUTES) <= window_end:
            slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)

            is_free = all(
                slot_start
                >= datetime.fromisoformat(b["end"]) + timedelta(minutes=MEETING_BUFFER_MINUTES)
                or slot_end + timedelta(minutes=MEETING_BUFFER_MINUTES)
                <= datetime.fromisoformat(b["start"])
                for b in busy_periods
            )

            if is_free:
                slots.append({
                    "start": slot_start.isoformat(),
                    "end": slot_end.isoformat(),
                    "display": slot_start.strftime("%A, %B %d at %I:%M %p ET"),
                })
                if len(slots) >= num_slots:
                    return slots

            slot_start = slot_end + timedelta(minutes=MEETING_BUFFER_MINUTES)

    return slots


def create_interview_event(
    start_iso: str,
    end_iso: str,
    visitor_name: str,
    visitor_email: Optional[str],
    company: str,
    role: str,
    summary_text: str,
) -> Optional[str]:
    """Create a Google Calendar event. Returns the event HTML link or None on failure."""
    service = _get_calendar_service()
    if not service:
        print("Google Calendar not configured, skipping event creation")
        return None

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    title = f"Interview: {company} — {role}" if company else f"Interview with {visitor_name or 'Visitor'}"
    event_body = {
        "summary": title,
        "description": (
            f"Scheduled by Career AI Twin\n\n"
            f"Contact: {visitor_name or 'Unknown'}\n"
            f"Email: {visitor_email or 'not provided'}\n"
            f"Company: {company or 'not provided'}\n"
            f"Role: {role or 'not provided'}\n\n"
            f"Conversation summary:\n{summary_text}"
        ),
        "start": {"dateTime": start_iso, "timeZone": "America/New_York"},
        "end": {"dateTime": end_iso, "timeZone": "America/New_York"},
    }

    if visitor_email:
        event_body["attendees"] = [{"email": visitor_email}]

    try:
        event = (
            service.events()
            .insert(
                calendarId=calendar_id,
                body=event_body,
                sendUpdates="all" if visitor_email else "none",
            )
            .execute()
        )
        return event.get("htmlLink")
    except Exception as e:
        print(f"Google Calendar event creation failed: {e}")
        return None
