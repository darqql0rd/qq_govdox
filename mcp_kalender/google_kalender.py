"""Google-Calendar-Zugriff für den Kalender-MCP-Server (Owner: Nayan).

Nur dieser Teil spricht mit Google. Der Agent selbst sieht weder credentials.json
noch token.json, er redet nur per MCP mit dem Server (mcp_kalender/server.py).

- credentials.json: OAuth-Client "Desktop-App" aus der Google Cloud Console
- token.json: entsteht beim einmaligen Login (python mcp_kalender/login.py)
Beide Dateien liegen im Repo-Root und stehen in .gitignore.
"""

import os
from datetime import date, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS = ROOT / "credentials.json"
TOKEN = ROOT / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]  # nur Termine, keine Kalender-Verwaltung
ZEITZONE = "Europe/Zurich"
ERINNERUNG_UHRZEIT = 9          # Erinnerung um 09:00 am Erinnerungstag
MAX_ERINNERUNG_MINUTEN = 40320  # Google erlaubt höchstens 4 Wochen vorher


class NichtAngemeldet(RuntimeError):
    pass


def anmeldedaten() -> Credentials:
    """Gespeichertes Login laden und bei Bedarf erneuern. Öffnet nie einen Browser.

    Der Server läuft als Unterprozess ohne Bildschirm; das Login im Browser macht
    login.py. Im Google-Status "Testing" läuft das Login nach 7 Tagen ab.
    """
    if not TOKEN.exists():
        raise NichtAngemeldet("token.json fehlt: einmal 'python mcp_kalender/login.py' ausführen")
    cred = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if cred.valid:
        return cred
    if cred.expired and cred.refresh_token:
        try:
            cred.refresh(Request())
        except Exception as fehler:
            raise NichtAngemeldet(
                f"Login abgelaufen ({fehler}): 'python mcp_kalender/login.py' erneut ausführen"
            ) from fehler
        TOKEN.write_text(cred.to_json())
        return cred
    raise NichtAngemeldet("Login ungültig: 'python mcp_kalender/login.py' erneut ausführen")


def kalender_id() -> str:
    return os.getenv("GOOGLE_CALENDAR_ID") or "primary"


def dienst():
    return build("calendar", "v3", credentials=anmeldedaten(), cache_discovery=False)


def erinnerung_minuten(datum: date, erinnerung: date | None) -> int:
    """Minuten vor Terminbeginn (Ganztagestermin = 00:00) bis Erinnerungstag 09:00."""
    if erinnerung is None or erinnerung >= datum:
        return (24 - ERINNERUNG_UHRZEIT) * 60  # am Vortag um 09:00
    minuten = (datum - erinnerung).days * 24 * 60 - ERINNERUNG_UHRZEIT * 60
    return max(0, min(minuten, MAX_ERINNERUNG_MINUTEN))


def _refs(referenzen: list[str]) -> set[str]:
    """Referenzen vergleichbar machen: ohne Leerzeichen, Grossbuchstaben."""
    return {"".join(r.split()).upper() for r in referenzen if r and r.strip()}


def termin_finden(svc, art: str, datum: date, referenzen: list[str]) -> dict | None:
    """Gleiche Frist schon eingetragen? Gleiche Art, gleicher Tag und eine gemeinsame Referenz.

    Nicht über einen festen Schlüssel aus allen Referenzen: Das LLM liest bei einem zweiten
    Lauf manchmal eine Referenz mehr oder weniger aus (z. B. zusätzlich die Rechnungsnummer).
    Hat eine Seite gar keine Referenz, genügen Art und Tag.
    """
    antwort = svc.events().list(
        calendarId=kalender_id(),
        privateExtendedProperty=[f"qq_art={art}", f"qq_datum={datum.isoformat()}"],
        showDeleted=False,
        maxResults=50,
    ).execute()
    neu = _refs(referenzen)
    for termin in antwort.get("items", []):
        alt = set(filter(None, termin["extendedProperties"]["private"].get("qq_refs", "").split("|")))
        if not alt or not neu or alt & neu:
            return termin
    return None


def termin_eintragen(titel: str, datum: date, beschreibung: str, erinnerung: date | None,
                     art: str, referenzen: list[str]) -> tuple[dict, bool]:
    """Ganztägigen Termin anlegen. Gibt (Termin, neu) zurück; existiert er schon, neu=False."""
    svc = dienst()
    vorhanden = termin_finden(svc, art, datum, referenzen)
    if vorhanden:
        return vorhanden, False
    termin = {
        "summary": titel,
        "description": beschreibung,
        "start": {"date": datum.isoformat()},
        "end": {"date": (datum + timedelta(days=1)).isoformat()},  # Ende ist exklusiv
        "reminders": {"useDefault": False, "overrides": [
            {"method": "popup", "minutes": erinnerung_minuten(datum, erinnerung)},
        ]},
        "extendedProperties": {"private": {
            "qq_govdox": "1",              # Markierung: von qq_govdox angelegt
            "qq_art": art,
            "qq_datum": datum.isoformat(),
            "qq_refs": "|".join(sorted(_refs(referenzen))),
        }},
        "transparency": "transparent",  # blockiert den Tag nicht als "beschäftigt"
    }
    return svc.events().insert(calendarId=kalender_id(), body=termin).execute(), True


def termine_auflisten(ab: date, bis: date) -> list[dict]:
    """Nur Termine, die qq_govdox selbst eingetragen hat."""
    antwort = dienst().events().list(
        calendarId=kalender_id(),
        timeMin=f"{ab.isoformat()}T00:00:00Z",
        timeMax=f"{bis.isoformat()}T23:59:59Z",
        singleEvents=True,
        orderBy="startTime",
        maxResults=250,
    ).execute()
    # Die API filtert nur nach Name=Wert, nicht nach "Eigenschaft vorhanden" -> hier filtern
    return [t for t in antwort.get("items", [])
            if "qq_govdox" in t.get("extendedProperties", {}).get("private", {})]


def termin_loeschen(event_id: str) -> None:
    """Löscht nur Termine, die qq_govdox selbst angelegt hat, nie fremde."""
    svc = dienst()
    termin = svc.events().get(calendarId=kalender_id(), eventId=event_id).execute()
    if "qq_govdox" not in termin.get("extendedProperties", {}).get("private", {}):
        raise PermissionError(f"Termin {event_id} wurde nicht von qq_govdox angelegt")
    svc.events().delete(calendarId=kalender_id(), eventId=event_id).execute()
