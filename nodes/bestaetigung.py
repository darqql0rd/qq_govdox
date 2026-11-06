"""Bestätigungs-Node (Owner: Melvin): Human-in-the-loop mit interrupt().

Zeigt der Person die berechneten Fristen und den Antwortentwurf und fragt Ja/Nein,
bevor etwas in den Kalender kommt. Team-Entscheid (Vorschlag): nur Ja/Nein, keine
Korrektur von Fristen oder Entwurf.

- Ja: Fristen werden als bestaetigt=True kopiert, der Graph geht zum Kalender.
- Nein: Ende mit abbruch_grund="nicht_bestaetigt".
- Nichts zu bestätigen (keine Fristen, kein Entwurf, z. B. unbekannter Brief):
  keine Frage, kein Kalender.

Beim Fortsetzen läuft der Node von vorne, vor dem interrupt() also keine Nebenwirkungen.
"""

from langgraph.types import interrupt

from state import Bestaetigung, BriefState

FRAGE = {
    "de": "Stimmen diese Fristen? Sollen sie in Ihren Kalender eingetragen werden? (ja/nein)",
    "fr": "Ces délais sont-ils corrects ? Faut-il les inscrire dans votre agenda ? (oui/non)",
    "it": "Questi termini sono corretti? Vuole inserirli nel Suo calendario? (sì/no)",
}

JA = {"ja", "j", "yes", "y", "oui", "o", "si", "sì", "true", "1"}


def ist_ja(antwort) -> bool:
    """Ja/Nein tolerant auswerten: True/False oder Text in DE/FR/IT/EN. Alles andere = Nein."""
    if isinstance(antwort, bool):
        return antwort
    return str(antwort).strip().lower().rstrip(".!") in JA


def bestaetigung(state: BriefState) -> dict:
    fristen = state.get("fristen", [])
    entwurf = state.get("antwortentwurf")
    if not fristen and not entwurf:
        return {"bestaetigung": Bestaetigung(bestaetigt=False)}

    sprache = state.get("nutzersprache", "de")
    antwort = interrupt({
        "typ": "bestaetigung",
        "frage": FRAGE.get(sprache, FRAGE["de"]),
        "sprache": sprache,
        "fristen": [f.model_dump(mode="json", include={"art", "datum", "hinweise"})
                    for f in fristen],
        "antwortentwurf": entwurf.model_dump(mode="json", include={"betreff", "text"})
        if entwurf else None,
    })

    if not ist_ja(antwort):
        return {"bestaetigung": Bestaetigung(bestaetigt=False),
                "abbruch_grund": "nicht_bestaetigt"}
    return {
        "bestaetigung": Bestaetigung(bestaetigt=True),
        # Kopien statt Änderung am bestehenden Objekt im State
        "fristen": [f.model_copy(update={"bestaetigt": True}) for f in fristen],
    }
