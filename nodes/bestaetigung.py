"""Bestätigungs-Node (Owner: Melvin) – PLATZHALTER aus dem Graph-Gerüst.

Sagt immer Ja. Später zeigt der Node Fristen und Antwortentwurf per interrupt()
und fragt Ja/Nein.
"""

from state import Bestaetigung, BriefState


def bestaetigung(state: BriefState) -> dict:
    return {"bestaetigung": Bestaetigung(bestaetigt=True)}
