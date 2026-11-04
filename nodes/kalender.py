"""Kalender-Node (Owner: Vendon) – PLATZHALTER aus dem Graph-Gerüst.

Legt noch keine Termine an. Später: Termine über den Kalender-MCP, Fallback .ics.
"""

from state import BriefState, KalenderErgebnis


def kalender(state: BriefState) -> dict:
    return {"kalender": KalenderErgebnis(kanal="ics")}
