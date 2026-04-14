#!/usr/bin/env python3
"""One-time helper to obtain a Google OAuth 2.0 refresh token for Calendar access.

Prerequisites:
  1. Go to https://console.cloud.google.com/apis/credentials
  2. Create an OAuth 2.0 Client ID (type: "Desktop app")
  3. Enable the Google Calendar API for your project

Usage:
  python scripts/google_oauth.py <client_id> <client_secret>

The script opens a browser for you to grant calendar access, then prints the
refresh token to paste into your .env / Terraform variables.
"""

import sys


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <client_id> <client_secret>")
        sys.exit(1)

    client_id = sys.argv[1]
    client_secret = sys.argv[2]

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Installing google-auth-oauthlib (needed only for this script)...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "google-auth-oauthlib"])
        from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    creds = flow.run_local_server(port=0, open_browser=True)

    print("\n--- Add these to your backend/.env ---\n")
    print(f"GOOGLE_OAUTH_CLIENT_ID={client_id}")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
    print()


if __name__ == "__main__":
    main()
