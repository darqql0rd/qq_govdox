"""Kalender-MCP-Server (Owner: Nayan): Fristen in den Google Kalender eintragen.

Eigener Prozess, spricht MCP über stdin/stdout. Der Kalender-Node startet ihn selbst
(nodes/kalender.py), man muss ihn nicht separat laufen lassen. Weil der Server ein
normaler MCP-Server ist, funktioniert er auch in anderen MCP-Clients (z. B. Claude
Desktop oder MCP Inspector).

    mcp dev mcp_kalender/server.py      # MCP Inspector im Browser, Tools von Hand testen

Wichtig: Nichts auf stdout schreiben (print), sonst geht das MCP-Protokoll kaputt.
"""

import json
import sys
import warnings
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore", category=FutureWarning, module="google")  # Python-3.10-Hinweis

from dotenv import load_dotenv  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from mcp_kalender import google_kalender as gk  # noqa: E402

load_dotenv(gk.ROOT / ".env")

mcp = FastMCP("qq_govdox-kalender", log_level="WARNING")  # INFO pro Aufruf stört die Ausgabe


@mcp.tool()
def frist_eintragen(titel: str, datum: str, beschreibung: str, art: str,
                    referenzen: list[str] | None = None, erinnerung: str | None = None) -> str:
    """Trägt eine Frist als ganztägigen Termin in den Google Kalender ein.

    Steht am selben Tag schon eine Frist derselben Art mit einer gemeinsamen Referenz,
    wird kein zweiter Termin angelegt (z. B. wenn derselbe Brief zweimal läuft).

    Args:
        titel: Titel des Termins, z. B. "Frist Rechtsvorschlag – Betreibungsamt Talwil"
        datum: letzter Tag der Frist, ISO-Format JJJJ-MM-TT
        beschreibung: Text im Termin (Rechtsgrundlage, Referenz, Betrag, Hinweise)
        art: Fristart, z. B. "rechtsvorschlag", "zahlung", "einsprache"
        referenzen: Nummern aus dem Brief (Betreibungs-Nr., Rechnungs-Nr., ...)
        erinnerung: Tag der Erinnerung (JJJJ-MM-TT), Erinnerung um 09:00. Ohne Angabe am Vortag.

    Returns:
        JSON mit event_id, link und neu (false, wenn der Termin schon bestand)
    """
    termin, neu = gk.termin_eintragen(
        titel=titel,
        datum=date.fromisoformat(datum),
        beschreibung=beschreibung,
        erinnerung=date.fromisoformat(erinnerung) if erinnerung else None,
        art=art,
        referenzen=referenzen or [],
    )
    return json.dumps({"event_id": termin["id"], "link": termin.get("htmlLink"), "neu": neu})


@mcp.tool()
def fristen_auflisten(tage: int = 365) -> str:
    """Listet die von qq_govdox eingetragenen Fristen ab heute für die nächsten `tage` Tage.

    Returns:
        JSON-Liste mit event_id, titel und datum
    """
    heute = date.today()
    termine = gk.termine_auflisten(heute, heute + timedelta(days=tage))
    return json.dumps([{"event_id": t["id"], "titel": t.get("summary"),
                        "datum": t["start"].get("date") or t["start"].get("dateTime")}
                       for t in termine], ensure_ascii=False)


@mcp.tool()
def frist_loeschen(event_id: str) -> str:
    """Löscht einen von qq_govdox eingetragenen Termin (z. B. nach einem Testlauf)."""
    gk.termin_loeschen(event_id)
    return json.dumps({"geloescht": event_id})


if __name__ == "__main__":
    mcp.run()  # Standard-Transport: stdio
