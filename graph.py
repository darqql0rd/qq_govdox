"""Graph-Gerüst mit allen 9 Nodes (Owner: Melvin).

OCR -> Analyse -> (Zustelldatum erfragen) -> Fristen -> Erklärung -> (Antwort)
-> Guardrail -> Bestätigung -> Kalender. Noch nicht fertige Nodes sind Platzhalter
in nodes/, die nur ihre eigenen Felder aus FELDER_PRO_NODE zurückgeben.

Die Routing-Funktionen lesen nur. abbruch_grund setzt der jeweilige Node selbst
(ocr: "unlesbar", guardrail: "guardrail_limit", bestaetigung: "nicht_bestaetigt").
Der Checkpointer (MemorySaver) ist Pflicht, sonst funktioniert interrupt() nicht.

    python graph.py      # Graph als Mermaid ausgeben
"""

import inspect

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

import state as state_modul
from llm import LLM_RETRY

from nodes.analyse import analyse
from nodes.antwort import antwort
from nodes.bestaetigung import bestaetigung
from nodes.erklaerung import erklaerung
from nodes.fristen import fristen
from nodes.guardrail import guardrail
from nodes.kalender import kalender
from nodes.ocr import ocr
from nodes.zustelldatum_erfragen import zustelldatum_erfragen
from state import MAX_VERSUCHE, BriefState

# Frist läuft ab Zustellung -> ohne Zustelldatum muss die Person gefragt werden
BRAUCHT_ZUSTELLDATUM = {"zahlungsbefehl", "steuerveranlagung"}
# Bei Mahnung und unbekannten Briefen gibt es keinen Antwortentwurf
BRAUCHT_ANTWORT = {"zahlungsbefehl", "steuerveranlagung", "krankenkasse_praemie"}

# Nach einem interrupt() lädt der Checkpointer den State neu. Unsere Pydantic-Modelle aus
# state.py ausdrücklich erlauben, sonst warnt LangGraph (und blockiert sie in Zukunft).
ERLAUBTE_MODELLE = [
    ("state", name) for name, klasse in inspect.getmembers(state_modul, inspect.isclass)
    if issubclass(klasse, BaseModel) and klasse.__module__ == "state"
]


def nach_ocr(state: BriefState) -> str:
    """Unlesbar -> nochmals OCR, bis MAX_VERSUCHE["ocr"] erreicht ist, dann Ende."""
    if state.get("text_lesbar"):
        return "analyse"
    if state.get("versuche", {}).get("ocr", 0) < MAX_VERSUCHE["ocr"]:
        return "ocr"
    return END


def nach_analyse(state: BriefState) -> str:
    """Unbekannt -> nur allgemeine Erklärung; fehlt das Zustelldatum -> nachfragen."""
    brieftyp = state.get("brieftyp")
    if brieftyp == "unbekannt":
        return "erklaerung"
    if brieftyp in BRAUCHT_ZUSTELLDATUM and state.get("zustelldatum") is None:
        return "zustelldatum_erfragen"
    return "fristen"


def nach_erklaerung(state: BriefState) -> str:
    """Antwortentwurf nur bei Zahlungsbefehl, Steuer und Krankenkasse."""
    return "antwort" if state.get("brieftyp") in BRAUCHT_ANTWORT else "guardrail"


def nach_guardrail(state: BriefState) -> str:
    """Bestanden -> Bestätigung; sonst gezielt zurück, solange Versuche übrig sind."""
    ergebnis = state.get("guardrail")
    if ergebnis is None or ergebnis.bestanden:
        return "bestaetigung"
    if state.get("versuche", {}).get("guardrail", 0) < MAX_VERSUCHE["guardrail"]:
        # "beide" -> zuerst Erklärung, die Antwort folgt über nach_erklaerung
        return "antwort" if ergebnis.zurueck_zu == "antwort" else "erklaerung"
    return END


def nach_bestaetigung(state: BriefState) -> str:
    """Nur bestätigte Briefe mit Fristen kommen in den Kalender."""
    b = state.get("bestaetigung")
    return "kalender" if b and b.bestaetigt and state.get("fristen") else END


def baue_graph(checkpointer=None):
    b = StateGraph(BriefState)
    # LLM_RETRY nur bei Nodes mit LLM-Aufruf. Nicht bei interrupt()-Nodes: ein Retry würde
    # die Frage an die Person nochmals stellen. OCR läuft lokal, Fristen sind reines Python.
    b.add_node("ocr", ocr)
    b.add_node("analyse", analyse, retry_policy=LLM_RETRY)
    b.add_node("zustelldatum_erfragen", zustelldatum_erfragen)
    b.add_node("fristen", fristen)
    b.add_node("erklaerung", erklaerung, retry_policy=LLM_RETRY)
    b.add_node("antwort", antwort, retry_policy=LLM_RETRY)
    b.add_node("guardrail", guardrail, retry_policy=LLM_RETRY)
    b.add_node("bestaetigung", bestaetigung)
    b.add_node("kalender", kalender)

    # Die Ziellisten braucht es, damit Mermaid die bedingten Kanten zeichnet
    b.add_edge(START, "ocr")
    b.add_conditional_edges("ocr", nach_ocr, ["ocr", "analyse", END])
    b.add_conditional_edges("analyse", nach_analyse,
                            ["erklaerung", "zustelldatum_erfragen", "fristen"])
    b.add_edge("zustelldatum_erfragen", "fristen")
    b.add_edge("fristen", "erklaerung")
    b.add_conditional_edges("erklaerung", nach_erklaerung, ["antwort", "guardrail"])
    b.add_edge("antwort", "guardrail")
    b.add_conditional_edges("guardrail", nach_guardrail,
                            ["bestaetigung", "erklaerung", "antwort", END])
    b.add_conditional_edges("bestaetigung", nach_bestaetigung, ["kalender", END])
    b.add_edge("kalender", END)
    if checkpointer is None:
        serde = JsonPlusSerializer(allowed_msgpack_modules=ERLAUBTE_MODELLE)
        checkpointer = MemorySaver(serde=serde)
    return b.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    print(baue_graph().get_graph().draw_mermaid())
