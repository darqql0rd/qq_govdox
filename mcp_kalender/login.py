"""Einmaliges Google-Login für den Kalender-MCP (Owner: Nayan).

Öffnet den Browser, man meldet sich mit dem Projekt-Konto an und erlaubt den Zugriff
auf die Kalendertermine. Danach liegt token.json im Repo-Root (steht in .gitignore).

    python mcp_kalender/login.py

Warnung "Google hat diese App nicht überprüft" ist bei Test-Apps normal:
Erweitert -> Weiter zu qq_govdox. Im Status "Testing" läuft das Login nach 7 Tagen ab,
dann dieses Script nochmals ausführen.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from mcp_kalender.google_kalender import CREDENTIALS, SCOPES, TOKEN, dienst, kalender_id  # noqa: E402

load_dotenv()

if not CREDENTIALS.exists():
    sys.exit(f"{CREDENTIALS} fehlt: OAuth-Client (Desktop-App) in der Google Cloud Console "
             "erstellen und als credentials.json in den Repo-Ordner legen.")

flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
cred = flow.run_local_server(port=0, prompt="consent")
TOKEN.write_text(cred.to_json())
print(f"Angemeldet, gespeichert in {TOKEN.name}.")

# Kurzer Test: Zugriff auf den eingestellten Kalender
dienst().events().list(calendarId=kalender_id(), maxResults=1).execute()
print(f"Zugriff auf Kalender '{kalender_id()}' funktioniert.")
