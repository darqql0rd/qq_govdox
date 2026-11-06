"""Einen oder mehrere Testbriefe durch den Graphen schicken und mit gold.json vergleichen.

    python main.py 01                 # ein Brief (Anfang der Fall-ID genügt)
    python main.py 01 02 03           # mehrere
    python main.py zahlungsbefehl     # alle Briefe, deren ID das Wort enthält
"""

import sys
from datetime import date
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()  # vor den LangChain-Imports, damit LangSmith-Tracing aktiv ist

from langgraph.types import Command             # noqa: E402

from graph import baue_graph                    # noqa: E402
from mocks import aus_gold, fall_ids, lade_gold  # noqa: E402
from state import FELDER_PRO_NODE               # noqa: E402

# Nur diese Felder gehen in den Graphen – alles andere muss der Agent selbst herausfinden.
# (aus_gold liefert auch die Gold-Extraktion; die darf der Agent nicht sehen.)
EINGABE = set(FELDER_PRO_NODE["eingabe"]) | set(FELDER_PRO_NODE["ocr"])


def vergleiche(fall: str, ende: dict) -> bool:
    gold = lade_gold(fall)
    erwartet = {(f["art"], f["datum"]) for f in gold["erwartete_fristen"]}
    erhalten = {(f.art, f.datum.isoformat()) for f in ende.get("fristen", [])}
    betrag = ende["extraktion"].hauptbetrag_chf if "extraktion" in ende else None
    gold_betrag = gold["extraktion"]["hauptbetrag_chf"]
    # Beide leer (z. B. Werbebrief ohne Betrag) zählt als richtig
    if betrag is None or gold_betrag is None:
        betrag_ok = betrag is None and gold_betrag is None
    else:
        betrag_ok = abs(betrag - gold_betrag) < 0.01
    checks = {
        "Brieftyp": ende.get("brieftyp") == gold["brieftyp"],
        "Fristen": erwartet == erhalten,
        "Betrag": betrag_ok,
        "Injection": ende.get("injection_verdacht") == gold["injection_verdacht"],
    }
    for name, ok in checks.items():
        print(f"  {'✓' if ok else '✗'} {name}")
    if not checks["Brieftyp"]:
        print(f"      Brieftyp erwartet {gold['brieftyp']}, erhalten {ende.get('brieftyp')}")
    if not checks["Fristen"]:
        print(f"      erwartet {sorted(erwartet)}\n      erhalten {sorted(erhalten)}")
    if not checks["Betrag"]:
        print(f"      Betrag erwartet {gold_betrag}, erhalten {betrag}")
    return all(checks.values())


def automatische_antwort(fall: str, frage: dict):
    """Beantwortet einen Interrupt so, wie es die Person im Testfall tun würde.

    Zustelldatum: die Annahme aus gold.json, als Text wie von Hand eingetippt.
    Bestätigung: immer Ja.
    """
    if frage["typ"] == "zustelldatum":
        annahme = lade_gold(fall).get("zustelldatum_annahme")
        return date.fromisoformat(annahme).strftime("%d.%m.%Y") if annahme else "weiss nicht"
    if frage["typ"] == "bestaetigung":
        return "ja"
    raise ValueError(f"Unbekannter Interrupt: {frage}")


def main(muster: list[str]):
    graph = baue_graph()
    faelle = [f for f in fall_ids() if any(f.startswith(m) or m in f for m in muster)]
    ok = 0
    for fall in faelle:
        print(f"\n=== {fall} ===")
        try:
            voll = aus_gold(fall, "pdf")
            start = {k: v for k, v in voll.items() if k in EINGABE}
            start.pop("versuche", None)  # zählt der OCR-Node selbst, sonst doppelt
            # Eigene thread_id pro Lauf: Der Checkpointer würde sonst bei einem zweiten Lauf
            # desselben Briefs (z. B. eval.py, 3 Läufe) den alten Thread fortsetzen.
            config = {"configurable": {"thread_id": f"{fall}-{uuid4().hex[:8]}"},
                      "run_name": fall, "tags": ["durchstich"]}
            ende = graph.invoke(start, config=config)
            # Human-in-the-loop: Der Graph hält bei jeder Frage an und wird mit der Antwort fortgesetzt
            while "__interrupt__" in ende:
                frage = ende["__interrupt__"][0].value
                antwort = automatische_antwort(fall, frage)
                print(f"  ? {frage['frage']}  -> {antwort}")
                ende = graph.invoke(Command(resume=antwort), config=config)
        except Exception as fehler:  # ein kaputter Brief (oder Gold-File) soll nicht den ganzen Lauf stoppen
            print(f"  ✗ ABSTURZ: {type(fehler).__name__}: {str(fehler)[:300]}")
            continue

        if "erklaerung" in ende:
            print(ende["erklaerung"].text)
            for s in ende["erklaerung"].naechste_schritte:
                print("  •", s)
        else:
            print(f"  (keine Erklärung – Abbruch: {ende.get('abbruch_grund')})")
        if ende.get("antwortentwurf"):
            print(f"  Antwortentwurf: {ende['antwortentwurf'].betreff}")
        ok += vergleiche(fall, ende)
    print(f"\n{ok}/{len(faelle)} Fälle vollständig korrekt")


if __name__ == "__main__":
    main(sys.argv[1:] or ["01"])
