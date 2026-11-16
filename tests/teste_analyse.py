"""Analyse-Node ohne LLM testen: Nachbearbeitung in Python.

1. Vorzeichen: Rückerstattung -> negativer Hauptbetrag (Läufe 16.11., Briefe 13 und 17).
2. zahlungsfrist_im_brief (Krankenkasse, Briefe 21/25) wird wie die anderen Daten eingelesen
   und landet als Frist "zahlung" im Fristen-Node.

    python tests/teste_analyse.py
"""

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.update(LLM_MODEL="test", LLM_BASE_URL="http://localhost:9/v1", LLM_API_KEY="test")

import nodes.analyse as analyse_modul  # noqa: E402
from nodes.fristen import fristen  # noqa: E402
from state import AnalyseErgebnis, Extraktion  # noqa: E402


def pruefe(name: str, ok: bool, detail: str = "") -> int:
    print(f"  {'✓' if ok else '✗'} {name}" + (f": {detail}" if detail else ""))
    return 0 if ok else 1


class FalschesLlm:
    def __init__(self, ergebnis):
        self.ergebnis = ergebnis

    def __call__(self, schema, model=None):
        return self

    def invoke(self, nachrichten):
        return self.ergebnis


def analysiere(extraktion: dict, brieftyp: str = "steuerveranlagung") -> dict:
    echt = analyse_modul.strukturiert
    try:
        analyse_modul.strukturiert = FalschesLlm(AnalyseErgebnis(
            brieftyp=brieftyp, brieftyp_konfidenz=1.0, briefsprache="de", extraktion=extraktion))
        return analyse_modul.analyse({"rohtext": "Testbrief"})
    finally:
        analyse_modul.strukturiert = echt


def teste_vorzeichen() -> int:
    f = 0
    e = analysiere({"hauptbetrag_chf": 638.20, "zahlungsrichtung": "rueckerstattung"})["extraktion"]
    f += pruefe("Rückerstattung positiv -> negativ", e.hauptbetrag_chf == -638.20, str(e.hauptbetrag_chf))
    e = analysiere({"hauptbetrag_chf": -401.50, "zahlungsrichtung": "rueckerstattung"})["extraktion"]
    f += pruefe("Rückerstattung schon negativ bleibt", e.hauptbetrag_chf == -401.50)
    e = analysiere({"hauptbetrag_chf": 2106.10, "zahlungsrichtung": "zu_zahlen"})["extraktion"]
    f += pruefe("Nachzahlung bleibt positiv", e.hauptbetrag_chf == 2106.10)
    return f


def teste_zahlungsfrist() -> int:
    f = 0
    for text in ("31. Dezember 2026", "31 décembre 2026", "31 dicembre 2026", "31.12.2026"):
        e = Extraktion(zahlungsfrist_im_brief=text)
        f += pruefe(f"Datum '{text}'", e.zahlungsfrist_im_brief == date(2026, 12, 31),
                    str(e.zahlungsfrist_im_brief))
    update = analysiere({"frist_im_brief": "30. November 2026",
                         "zahlungsfrist_im_brief": "31. Dezember 2026",
                         "zahlungsrichtung": "zu_zahlen", "hauptbetrag_chf": 408.70},
                        brieftyp="krankenkasse_praemie")
    arten = {x.art: x.datum for x in fristen(update)["fristen"]}
    f += pruefe("Fristen-Node: Kündigung, Franchise, Zahlung",
                arten == {"kuendigung": date(2026, 11, 30), "franchise_wechsel": date(2026, 12, 31),
                          "zahlung": date(2026, 12, 31)}, str(sorted(arten)))
    return f


if __name__ == "__main__":
    fehler = teste_vorzeichen() + teste_zahlungsfrist()
    print("Alle Tests bestanden" if fehler == 0 else f"{fehler} Fehler")
    sys.exit(1 if fehler else 0)
