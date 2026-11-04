"""Antwort-Agent (Owner: Melvin) – PLATZHALTER aus dem Graph-Gerüst.

Liefert noch keinen Entwurf. Der echte Agent bekommt nur Extraktion und Fristen,
keinen Rohtext (Schutz vor Prompt Injection).
"""

from state import BriefState


def antwort(state: BriefState) -> dict:
    return {"antwortentwurf": None}
