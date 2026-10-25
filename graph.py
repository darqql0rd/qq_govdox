"""Graph für den Durchstich: Analyse -> Fristen -> Erklärung.

OCR, Antwort, Guardrail, Bestätigung und Kalender kommen später dazu.
Die Routing-Logik ist dieselbe wie im Skelett (notebooks/00_state_und_mocks.ipynb).
"""

from langgraph.graph import END, START, StateGraph

from nodes.analyse import analyse
from nodes.erklaerung import erklaerung
from nodes.fristen import fristen
from state import BriefState


def nach_analyse(state: BriefState) -> str:
    if state["brieftyp"] == "unbekannt":
        return "erklaerung"          # nur allgemeine Hilfe, keine Frist
    braucht_zustellung = state["brieftyp"] in ("zahlungsbefehl", "steuerveranlagung")
    if braucht_zustellung and state.get("zustelldatum") is None:
        return END                   # TODO: Node zustelldatum_erfragen (Human-in-the-loop, SW8)
    return "fristen"


def baue_graph():
    b = StateGraph(BriefState)
    b.add_node("analyse", analyse)
    b.add_node("fristen", fristen)
    b.add_node("erklaerung", erklaerung)

    b.add_edge(START, "analyse")
    b.add_conditional_edges("analyse", nach_analyse, ["fristen", "erklaerung", END])
    b.add_edge("fristen", "erklaerung")
    b.add_edge("erklaerung", END)
    return b.compile()


if __name__ == "__main__":
    print(baue_graph().get_graph().draw_mermaid())
