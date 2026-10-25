"""Erklär-Node (Owner: Vendon): Erklärung in einfacher Sprache.

Bekommt nur geprüfte Fakten (Extraktion + Fristen), NICHT den Rohtext des Briefs.
So kann eine Prompt Injection im Brief die Erklärung nicht direkt beeinflussen.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from llm import strukturiert
from prompts import ERKLAER_SYSTEM
from state import BriefState, Erklaerung


def erklaerung(state: BriefState) -> dict:
    fakten = {
        "ausgabesprache": state.get("nutzersprache", state["briefsprache"]),
        "brieftyp": state["brieftyp"],
        "brieftyp_vermutung": state.get("brieftyp_vermutung"),
        "zustelldatum": state.get("zustelldatum"),
        "zustelldatum_quelle": state.get("zustelldatum_quelle"),
        "extraktion": state["extraktion"].model_dump(mode="json", exclude={"belege"},
                                                     exclude_none=True),
        "fristen": [f.model_dump(mode="json", exclude={"bestaetigt", "erinnerung"})
                    for f in state.get("fristen", [])],
    }
    llm = strukturiert(Erklaerung)
    ergebnis: Erklaerung = llm.invoke([
        SystemMessage(ERKLAER_SYSTEM),
        HumanMessage(json.dumps(fakten, ensure_ascii=False, indent=2, default=str)),
    ])
    return {"erklaerung": ergebnis}
