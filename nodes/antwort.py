"""Antwort-Agent (Owner: Melvin): Entwurf für Rechtsvorschlag, Einsprache oder Kündigung.

Bekommt nur geprüfte Fakten (Extraktion + Fristen), NICHT den Rohtext des Briefs.
So kann eine Prompt Injection im Brief den Entwurf nicht direkt beeinflussen.

Was sich aus dem Brieftyp ergibt, legt Python fest und nicht das LLM: Art der Antwort,
Sprache, Empfänger und die Liste der Platzhalter. Das LLM schreibt nur Betreff und Text.
Bei fehlenden Eingaben oder einem LLM-Fehler bleibt antwortentwurf None statt Absturz.
"""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from llm import strukturiert
from prompts import ANTWORT_SYSTEM
from state import Antwortentwurf, BriefState

ART = {
    "zahlungsbefehl": "rechtsvorschlag",
    "steuerveranlagung": "einsprache",
    "krankenkasse_praemie": "kuendigung",
}

# Amtlicher Fachbegriff pro Sprache. Fest vorgegeben, weil Haiku in FR/IT-Briefen sonst
# deutsche Begriffe übernahm oder falsche wählte ("rigetto" statt "opposizione").
FACHBEGRIFF = {
    "rechtsvorschlag": {"de": "Rechtsvorschlag", "fr": "opposition", "it": "opposizione"},
    "einsprache": {"de": "Einsprache", "fr": "réclamation", "it": "reclamo"},
    "kuendigung": {"de": "Kündigung", "fr": "résiliation", "it": "disdetta"},
}
SPRACHNAME = {"de": "Deutsch", "fr": "Französisch", "it": "Italienisch"}


def antwort(state: BriefState) -> dict:
    art = ART.get(state.get("brieftyp"))
    extraktion = state.get("extraktion")
    if art is None or extraktion is None:
        return {"antwortentwurf": None}

    sprache = state.get("antwortsprache") or state.get("briefsprache", "de")
    fakten = {
        "antwortsprache": f"{sprache} ({SPRACHNAME.get(sprache, sprache)})",
        "brieftyp": state["brieftyp"],
        "art": art,
        "fachbegriff": FACHBEGRIFF[art].get(sprache, FACHBEGRIFF[art]["de"]),
        "extraktion": extraktion.model_dump(mode="json", exclude={"belege"}, exclude_none=True),
        "fristen": [f.model_dump(mode="json", include={"art", "datum", "hinweise", "rechtsgrundlage"})
                    for f in state.get("fristen", [])],
    }
    # Zweiter Versuch nach dem Guardrail: nur die Verstösse, die den Entwurf betreffen
    guardrail = state.get("guardrail")
    if guardrail and not guardrail.bestanden:
        fakten["feedback_guardrail"] = [v.model_dump() for v in guardrail.verstoesse
                                        if v.betrifft == "antwortentwurf"]

    try:
        entwurf: Antwortentwurf = strukturiert(Antwortentwurf).invoke([
            SystemMessage(ANTWORT_SYSTEM),
            HumanMessage(json.dumps(fakten, ensure_ascii=False, indent=2, default=str)),
        ])
    except Exception as fehler:  # ein Entwurf ist optional, der Graph soll weiterlaufen
        print(f"  ! Antwort-Agent: {type(fehler).__name__}: {str(fehler)[:200]}")
        return {"antwortentwurf": None}

    return {"antwortentwurf": entwurf.model_copy(update={
        "art": art,
        "sprache": sprache,
        "empfaenger": extraktion.absender or entwurf.empfaenger,
        "teilbetrag_chf": None,
        # Platzhalter aus dem Text lesen statt dem LLM zu glauben
        "platzhalter": list(dict.fromkeys(re.findall(r"\[[^\[\]\n]{1,40}\]", entwurf.text))),
    })}
