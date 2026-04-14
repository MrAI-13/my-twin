import os
import json
import urllib.request
import urllib.parse


PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"


def send_pushover(title: str, message: str) -> bool:
    """Send a push notification via Pushover. Returns True on success."""
    token = os.getenv("PUSHOVER_APP_TOKEN", "")
    user = os.getenv("PUSHOVER_USER_KEY", "")
    if not token or not user:
        print("Pushover credentials not configured, skipping notification")
        return False

    data = urllib.parse.urlencode({
        "token": token,
        "user": user,
        "title": title,
        "message": message[:1024],
        "priority": 0,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(PUSHOVER_API_URL, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("status") == 1
    except Exception as e:
        print(f"Pushover notification failed: {e}")
        return False
