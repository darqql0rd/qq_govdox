"""Kalender-Node (Owner: Nayan): bestätigte Fristen in den Kalender eintragen.

Ablauf:
- KALENDER_KANAL=google (.env): Der Node startet den Kalender-MCP-Server
  (mcp_kalender/server.py) als Unterprozess und ruft dessen Tool "frist_eintragen"
  pro Frist auf (langchain-mcp-adapters, stdio).
- Sonst (Standard) oder wenn Google scheitert: .ics-Datei in ausgabe/, die man in
  jeden Kalender importieren kann. Der Agent stürzt wegen des Kalenders nie ab.

Bewusste Entscheide:
- Datum und Erinnerung kommen direkt aus den berechneten Fristen, nicht vom LLM.
  Das Tool wird deterministisch aufgerufen (wie der Fristenrechner im Fristen-Node);
  ein LLM würde hier nur Datumsfehler riskieren. Titel und Beschreibung aus Vorlage.
- Standard ist .ics, damit Testläufe über 45 Briefe nicht den echten Kalender füllen.
- Fester Schlüssel pro Frist: ein zweiter Lauf desselben Briefs legt keinen
  doppelten Termin an.
"""

import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from state import BriefState, Frist, KalenderErgebnis

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "mcp_kalender" / "server.py"
AUSGABE = ROOT / "ausgabe"

TITEL = {
    "rechtsvorschlag": {"de": "Frist Rechtsvorschlag", "fr": "Délai d'opposition",
                        "it": "Termine per l'opposizione"},
    "zahlung": {"de": "Frist Zahlung", "fr": "Délai de paiement", "it": "Termine di pagamento"},
    "einsprache": {"de": "Frist Einsprache", "fr": "Délai de réclamation",
                   "it": "Termine per il reclamo"},
    "kuendigung": {"de": "Frist Kündigung Krankenkasse", "fr": "Délai de résiliation caisse maladie",
                   "it": "Termine disdetta cassa malati"},
    "franchise_wechsel": {"de": "Frist Franchise-/Modellwechsel",
                          "fr": "Délai changement de franchise/modèle",
                          "it": "Termine cambio franchigia/modello"},
}

TEXT = {
    "de": {"referenz": "Referenz", "betrag": "Betrag", "rechtsgrundlage": "Rechtsgrundlage",
           "eingang": "Wichtig: Das Schreiben muss bis zu diesem Tag EINGETROFFEN sein, "
                      "der Poststempel genügt nicht.",
           "geschaetzt": "Achtung: Zustelldatum geschätzt, Frist bitte prüfen.",
           "fuss": "Automatisch eingetragen von qq_govdox. Keine Rechtsberatung."},
    "fr": {"referenz": "Référence", "betrag": "Montant", "rechtsgrundlage": "Base légale",
           "eingang": "Important : le courrier doit être PARVENU à cette date, "
                      "le cachet postal ne suffit pas.",
           "geschaetzt": "Attention : date de notification estimée, vérifiez le délai.",
           "fuss": "Inscrit automatiquement par qq_govdox. Pas de conseil juridique."},
    "it": {"referenz": "Riferimento", "betrag": "Importo", "rechtsgrundlage": "Base legale",
           "eingang": "Importante: lo scritto deve essere PERVENUTO entro questa data, "
                      "il timbro postale non basta.",
           "geschaetzt": "Attenzione: data di notifica stimata, verificare il termine.",
           "fuss": "Inserito automaticamente da qq_govdox. Nessuna consulenza legale."},
}


def _sprache(state: BriefState) -> str:
    return state.get("nutzersprache") or state.get("briefsprache") or "de"


def schluessel(*teile: str) -> str:
    """Fester Schlüssel pro Frist, damit ein zweiter Lauf keinen doppelten Termin anlegt."""
    return hashlib.sha256("|".join(teile).encode()).hexdigest()[:16]


def termin_daten(frist: Frist, state: BriefState) -> dict:
    """Argumente für das MCP-Tool frist_eintragen (auch Grundlage für .ics)."""
    sprache = _sprache(state)
    t = TEXT[sprache]
    e = state.get("extraktion")
    absender = e.absender if e else None
    referenzen = [r.wert for r in e.referenzen] if e else []

    titel = TITEL[frist.art][sprache] + (f" – {absender}" if absender else "")
    zeilen = []
    if referenzen:
        zeilen.append(f"{t['referenz']}: {', '.join(referenzen)}")
    if e and e.hauptbetrag_chf is not None:
        zeilen.append(f"{t['betrag']}: CHF {e.hauptbetrag_chf:,.2f}".replace(",", "'"))
    if frist.rechtsgrundlage:
        zeilen.append(f"{t['rechtsgrundlage']}: {frist.rechtsgrundlage}")
    if "eingang_massgebend" in frist.hinweise:
        zeilen.append(t["eingang"])
    if "zustelldatum_geschaetzt" in frist.hinweise:
        zeilen.append(t["geschaetzt"])
    zeilen += ["", t["fuss"]]

    return {
        "titel": titel,
        "datum": frist.datum.isoformat(),
        "beschreibung": "\n".join(zeilen),
        "schluessel": schluessel(frist.art, frist.datum.isoformat(), absender or "",
                                 *sorted(referenzen)),
        "erinnerung": frist.erinnerung.isoformat() if frist.erinnerung else None,
    }


# ---------------------------------------------------------------------------
# Google Kalender über MCP
# ---------------------------------------------------------------------------

def _text(ergebnis) -> str:
    """Tool-Ergebnis der Adapter: je nach Version str oder Liste von Content-Blöcken."""
    if isinstance(ergebnis, str):
        return ergebnis
    if isinstance(ergebnis, (list, tuple)):
        return "".join(b.get("text", "") if isinstance(b, dict) else getattr(b, "text", str(b))
                       for b in ergebnis)
    return str(ergebnis)


async def _per_mcp(termine: list[dict]) -> list[str]:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools

    client = MultiServerMCPClient({"kalender": {
        "command": sys.executable,           # dasselbe Python/venv wie der Agent
        "args": [str(SERVER)],
        "transport": "stdio",
        "cwd": str(ROOT),
    }})
    event_ids = []
    async with client.session("kalender") as session:   # ein Serverprozess für alle Fristen
        tools = {t.name: t for t in await load_mcp_tools(session)}
        for termin in termine:
            antwort = _text(await tools["frist_eintragen"].ainvoke(termin))
            try:
                event_ids.append(json.loads(antwort)["event_id"])
            except (ValueError, KeyError, TypeError):
                raise RuntimeError(f"Kalender-MCP: {antwort[:300]}") from None
    return event_ids


def _ursache(e: BaseException) -> BaseException:
    """Aus den verschachtelten ExceptionGroups von anyio/MCP den eigentlichen Fehler holen."""
    while getattr(e, "exceptions", None):
        e = e.exceptions[0]
    return e


def _async_ausfuehren(coro):
    """asyncio.run, auch wenn schon eine Event-Loop läuft (Jupyter): dann in eigenem Thread."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(1) as pool:
        return pool.submit(asyncio.run, coro).result()


# ---------------------------------------------------------------------------
# Fallback: .ics-Datei
# ---------------------------------------------------------------------------

def _ics_text(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_schreiben(termine: list[dict], state: BriefState) -> str:
    e = state.get("extraktion")
    ref = e.referenzen[0].wert if e and e.referenzen else datetime.now().strftime("%Y%m%d-%H%M%S")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{state.get('brieftyp', 'brief')}_{ref}")
    pfad = AUSGABE / f"{name}.ics"
    stempel = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    zeilen = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//qq_govdox//Fristen//DE",
              "CALSCALE:GREGORIAN"]
    for t in termine:
        tag = date.fromisoformat(t["datum"])
        erinnerung = date.fromisoformat(t["erinnerung"]) if t["erinnerung"] else tag - timedelta(days=1)
        zeilen += [
            "BEGIN:VEVENT",
            f"UID:{t['schluessel']}@qq_govdox",
            f"DTSTAMP:{stempel}",
            f"DTSTART;VALUE=DATE:{tag:%Y%m%d}",
            f"DTEND;VALUE=DATE:{tag + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_ics_text(t['titel'])}",
            f"DESCRIPTION:{_ics_text(t['beschreibung'])}",
            "TRANSP:TRANSPARENT",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_ics_text(t['titel'])}",
            f"TRIGGER;VALUE=DATE-TIME:{erinnerung:%Y%m%d}T090000",
            "END:VALARM",
            "END:VEVENT",
        ]
    zeilen.append("END:VCALENDAR")
    AUSGABE.mkdir(exist_ok=True)
    pfad.write_text("\r\n".join(zeilen) + "\r\n", encoding="utf-8")
    return str(pfad.relative_to(ROOT))


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def kalender(state: BriefState) -> dict:
    fristen = [f for f in state.get("fristen", []) if f.bestaetigt]
    if not fristen:
        return {"kalender": KalenderErgebnis(kanal="ics", fehler="keine bestätigten Fristen")}
    termine = [termin_daten(f, state) for f in fristen]

    fehler = None
    if os.getenv("KALENDER_KANAL", "ics").lower() == "google":
        try:
            ids = _async_ausfuehren(_per_mcp(termine))
            return {"kalender": KalenderErgebnis(kanal="google_calendar_mcp", event_ids=ids)}
        except Exception as e:  # Google/MCP nicht erreichbar -> .ics statt Absturz
            e = _ursache(e)
            fehler = f"{type(e).__name__}: {str(e)[:300]}"
            print(f"  ! Kalender: Google nicht möglich, schreibe .ics ({fehler})")

    return {"kalender": KalenderErgebnis(kanal="ics", ics_pfad=ics_schreiben(termine, state),
                                         fehler=fehler)}
