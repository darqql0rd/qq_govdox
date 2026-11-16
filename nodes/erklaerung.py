"""Erklär-Node (Owner: Vendon): Erklärung in einfacher Sprache.

Bekommt nur geprüfte Fakten (Extraktion + Fristen), NICHT den Rohtext des Briefs.
So kann eine Prompt Injection im Brief die Erklärung nicht direkt beeinflussen.

Den Hinweis "Prototyp der FHNW, kein offizieller Dienst" hängt Python an (HINWEIS_PROTOTYP).
"""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from llm import strukturiert
from prompts import ERKLAER_SYSTEM, HINWEIS_PROTOTYP
from state import BriefState, Erklaerung


def ohne_hinweis(text: str) -> str:
    """Prototyp-Hinweis entfernen, falls das LLM ihn selbst geschrieben oder übernommen hat.

    Lauf 16.11.: Nach jedem Neuversuch stand der Hinweis doppelt da (06, 07, 09, 24, 25), weil die
    bisherige Erklärung mit Hinweis ans LLM ging und Python ihn danach nochmals anhängte.
    """
    for hinweis in HINWEIS_PROTOTYP.values():
        text = text.replace(hinweis, "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


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
    # Zweiter Versuch: Beanstandungen des Guardrails mitgeben
    g = state.get("guardrail")
    if g is not None and not g.bestanden:
        korrekturen = [v.detail for v in g.verstoesse if v.betrifft == "erklaerung"]
        if korrekturen and state.get("erklaerung"):
            bisher = state["erklaerung"].model_dump(mode="json", include={"text", "naechste_schritte"})
            bisher["text"] = ohne_hinweis(bisher["text"])  # hängt Python wieder an
            fakten["bisherige_erklaerung"] = bisher
            fakten["korrekturen"] = korrekturen
    llm = strukturiert(Erklaerung)
    ergebnis: Erklaerung = llm.invoke([
        SystemMessage(ERKLAER_SYSTEM),
        HumanMessage(json.dumps(fakten, ensure_ascii=False, indent=2, default=str)),
    ])
    # Fester Hinweis aus Python statt vom LLM: steht so immer gleich und in der richtigen Sprache
    sprache = fakten["ausgabesprache"] or ergebnis.sprache or "de"  # verlangte Sprache zählt
    hinweis = HINWEIS_PROTOTYP.get(sprache, HINWEIS_PROTOTYP["de"])
    text = ohne_hinweis(ergebnis.text)
    return {"erklaerung": ergebnis.model_copy(update={"text": f"{text}\n\n{hinweis}"})}
