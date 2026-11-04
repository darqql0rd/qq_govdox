"""Guardrail-Node (Owner: Florian) – PLATZHALTER aus dem Graph-Gerüst.

Lässt alles durch und zählt den Versuch. Der echte Node setzt bei Verstössen
zurueck_zu und nach MAX_VERSUCHE["guardrail"] selbst abbruch_grund="guardrail_limit".
"""

from state import BriefState, GuardrailErgebnis


def guardrail(state: BriefState) -> dict:
    return {"guardrail": GuardrailErgebnis(bestanden=True), "versuche": {"guardrail": 1}}
