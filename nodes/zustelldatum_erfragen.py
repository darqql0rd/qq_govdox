"""Zustelldatum erfragen (Owner: Melvin) – PLATZHALTER aus dem Graph-Gerüst.

Wird nur bei Zahlungsbefehl und Steuer ohne Zustelldatum erreicht. Später fragt der
Node die Person per interrupt(); bis dahin gilt das Briefdatum als Schätzung, damit
der Fristenrechner den Hinweis "zustelldatum_geschaetzt" ausgibt.
"""

from state import BriefState


def zustelldatum_erfragen(state: BriefState) -> dict:
    extraktion = state.get("extraktion")
    return {
        "zustelldatum": extraktion.briefdatum if extraktion else None,
        "zustelldatum_quelle": "geschaetzt",
    }
