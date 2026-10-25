"""Fristen-Node (Owner: Vendon): ruft den Fristenrechner auf – ohne LLM.

Bewusster Entscheid: Das Tool wird hier deterministisch aufgerufen und nicht vom
LLM ausgewählt (Fristen dürfen nicht vom Modell abhängen). Es ist trotzdem als
@tool definiert, damit es später auch ein Agent per bind_tools nutzen kann.
"""

from fristenrechner import fristen_berechnen
from state import BriefState, Frist


def fristen(state: BriefState) -> dict:
    e = state["extraktion"]
    roh = fristen_berechnen.invoke({
        "brieftyp": state["brieftyp"],
        "zustelldatum": state.get("zustelldatum"),
        "frist_im_brief": e.frist_im_brief,
        "zustelldatum_geschaetzt": state.get("zustelldatum_quelle") == "geschaetzt",
    })
    return {"fristen": [Frist(**f) for f in roh]}
