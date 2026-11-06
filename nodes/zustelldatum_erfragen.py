"""Zustelldatum erfragen (Owner: Melvin): Human-in-the-loop mit interrupt().

Wird nur bei Zahlungsbefehl und Steuer erreicht, wenn kein Zustelldatum im Brief steht
(beim Zahlungsbefehl ist "Zugestellt am" meist ein leeres Formularfeld). Die Frist läuft
ab Zustellung, also fragt der Graph die Person in ihrer Sprache.

Die Antwort wandelt parse_datum (datum.py) um, nicht das LLM. Weiss die Person es nicht,
gilt das Briefdatum als Schätzung: Die Frist wird damit eher zu früh als zu spät
berechnet (gleicher Grundsatz wie im Fristenrechner), und der Fristenrechner gibt den
Hinweis "zustelldatum_geschaetzt" aus.

Achtung: Beim Fortsetzen (Command(resume=...)) läuft der Node von vorne. Vor dem
interrupt() deshalb keine Nebenwirkungen.
"""

from langgraph.types import interrupt

from datum import parse_datum
from state import BriefState

FRAGE = {
    "de": "Wann haben Sie den Brief erhalten? (z. B. 18.11.2026 oder «weiss nicht»)",
    "fr": "Quand avez-vous reçu la lettre ? (p. ex. 18.11.2026 ou « je ne sais pas »)",
    "it": "Quando ha ricevuto la lettera? (p. es. 18.11.2026 o «non lo so»)",
}


def zustelldatum_erfragen(state: BriefState) -> dict:
    sprache = state.get("nutzersprache", "de")
    extraktion = state.get("extraktion")
    briefdatum = extraktion.briefdatum if extraktion else None

    antwort = interrupt({
        "typ": "zustelldatum",
        "frage": FRAGE.get(sprache, FRAGE["de"]),
        "sprache": sprache,
        "brieftyp": state.get("brieftyp"),
        "briefdatum": briefdatum.isoformat() if briefdatum else None,
    })

    try:
        datum = parse_datum(antwort)
    except ValueError:
        datum = None  # "weiss nicht", leer oder unlesbar
    # Zugestellt vor dem Briefdatum ist unmöglich -> wie "weiss nicht" behandeln
    if datum and briefdatum and datum < briefdatum:
        datum = None

    if datum:
        return {"zustelldatum": datum, "zustelldatum_quelle": "nutzer"}
    # Ohne Briefdatum keine Schätzung: lieber keine Frist als eine zu späte
    return {"zustelldatum": briefdatum, "zustelldatum_quelle": "geschaetzt" if briefdatum else None}
