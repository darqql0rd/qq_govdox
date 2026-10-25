"""Analyse-Node (Owner: Nayan): Klassifikation + Extraktion in einem LLM-Aufruf."""

from langchain_core.messages import HumanMessage, SystemMessage

from llm import strukturiert
from prompts import ANALYSE_SYSTEM
from state import AnalyseErgebnis, BriefState


def analyse(state: BriefState) -> dict:
    llm = strukturiert(AnalyseErgebnis)
    nachrichten = [
        SystemMessage(ANALYSE_SYSTEM),
        # Brief klar abgegrenzt: nicht vertrauenswürdige Eingabe (Prompt Injection)
        HumanMessage(f"<brief>\n{state['rohtext']}\n</brief>"),
    ]
    ergebnis: AnalyseErgebnis = llm.invoke(nachrichten)
    e = ergebnis.extraktion

    update = {
        "brieftyp": ergebnis.brieftyp,
        "brieftyp_konfidenz": ergebnis.brieftyp_konfidenz,
        "brieftyp_vermutung": ergebnis.brieftyp_vermutung,
        "briefsprache": ergebnis.briefsprache,
        "antwortsprache": ergebnis.briefsprache,
        "injection_verdacht": ergebnis.injection_verdacht,
        "extraktion": e,
    }
    # Zustelldatum: aus dem Brief, sonst eine Nutzerangabe behalten, die schon im State steht
    if e.zustelldatum_im_brief:
        update["zustelldatum"] = e.zustelldatum_im_brief
        update["zustelldatum_quelle"] = "brief"
    elif not state.get("zustelldatum"):
        update["zustelldatum"] = None
        update["zustelldatum_quelle"] = None

    # Deterministischer Plausibilitätscheck (False = Summe der Posten ≠ Hauptbetrag)
    if e.posten_plausibel() is False:
        print("  ! Analyse: Summe der Posten passt nicht zum Hauptbetrag")
    return update
