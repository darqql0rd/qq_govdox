"""Einen oder mehrere Testbriefe durch den Graphen schicken und mit gold.json vergleichen.

    python main.py 01                 # ein Brief (Anfang der Fall-ID genügt)
    python main.py 01 02 03           # mehrere
    python main.py zahlungsbefehl     # alle Briefe, deren ID das Wort enthält
"""

import sys
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # vor den LangChain-Imports, damit LangSmith-Tracing aktiv ist

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


def main(muster: list[str]):
    graph = baue_graph()
    faelle = [f for f in fall_ids() if any(f.startswith(m) or m in f for m in muster)]
    ok = 0
    for fall in faelle:
        print(f"\n=== {fall} ===")
        try:
            voll = aus_gold(fall, "pdf")
            start = {k: v for k, v in voll.items() if k in EINGABE}
            # Platzhalter für den Node zustelldatum_erfragen: Steht kein Zustelldatum im Brief,
            # tun wir so, als hätte die Person es angegeben (wie aus_gold es vorsieht).
            if voll.get("zustelldatum_quelle") == "nutzer":
                start["zustelldatum"] = voll["zustelldatum"]
                start["zustelldatum_quelle"] = "nutzer"
            ende = graph.invoke(start, config={"run_name": fall, "tags": ["durchstich"]})
        except Exception as fehler:  # ein kaputter Brief (oder Gold-File) soll nicht den ganzen Lauf stoppen
            print(f"  ✗ ABSTURZ: {type(fehler).__name__}: {str(fehler)[:300]}")
            continue

        if "erklaerung" in ende:
            print(ende["erklaerung"].text)
            for s in ende["erklaerung"].naechste_schritte:
                print("  •", s)
        else:
            print("  (keine Erklärung – Zustelldatum fehlt, Node zustelldatum_erfragen kommt noch)")
        ok += vergleiche(fall, ende)
    print(f"\n{ok}/{len(faelle)} Fälle vollständig korrekt")


if __name__ == "__main__":
    main(sys.argv[1:] or ["01"])
