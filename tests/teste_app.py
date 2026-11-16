"""UI (app.py) durchklicken, ohne LLM und ohne docTR (Streamlit AppTest).

Die LLM-Aufrufe liefern Antworten aus gold.json, die Texterkennung liest text.txt.
Geprüft wird der Ablauf: Beispielbrief wählen -> (Zustelldatum) -> Ergebnis ->
Bestätigung -> .ics-Download; dazu Sonderfälle (unbekannter Brief, Fallback).

    python tests/teste_app.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.update(LLM_MODEL="test", LLM_BASE_URL="http://localhost:9/v1", LLM_API_KEY="test",
                  GUARDRAIL_LLM="0", KALENDER_KANAL="ics", LANGSMITH_TRACING="false",
                  LANGCHAIN_TRACING_V2="false")

from streamlit.testing.v1 import AppTest  # noqa: E402

import nodes.analyse as analyse_modul  # noqa: E402
import nodes.antwort as antwort_modul  # noqa: E402
import nodes.erklaerung as erklaer_modul  # noqa: E402
import nodes.guardrail as guardrail_modul  # noqa: E402
import nodes.ocr as ocr_modul  # noqa: E402
from mocks import DATEN, lade_gold  # noqa: E402
from state import AnalyseErgebnis, Antwortentwurf, Erklaerung, GuardrailErgebnis, Verstoss  # noqa: E402

FALL = {"id": None}


class FalschesLlm:
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, nachrichten):
        g = lade_gold(FALL["id"])
        if self.schema is AnalyseErgebnis:
            ex = dict(g["extraktion"])
            ex["zustelldatum_im_brief"] = ex.get("zustelldatum_im_brief")
            return AnalyseErgebnis(brieftyp=g["brieftyp"], brieftyp_konfidenz=1.0,
                                   brieftyp_vermutung=g.get("brieftyp_vermutung"),
                                   briefsprache=g["briefsprache"],
                                   injection_verdacht=g.get("injection_verdacht", False),
                                   extraktion=ex)
        if self.schema is Erklaerung:
            return Erklaerung(sprache="de", text="Testerklärung.",
                              naechste_schritte=["Schritt eins."])
        if self.schema is Antwortentwurf:
            return Antwortentwurf(sprache="de", empfaenger="Amt", betreff="Testbetreff",
                                  text="[Name]\nTestentwurf", art="rechtsvorschlag")
        raise AssertionError(self.schema)


def falsche_texterkennung(pfade):
    return {"textquelle": "pdf_text", "seiten": 1, "text_lesbar": True, "text_konfidenz": None,
            "rohtext": (Path(pfade[0]).parent / "text.txt").read_text(encoding="utf-8")}


for modul in (analyse_modul, erklaer_modul, antwort_modul):
    modul.strukturiert = lambda schema, model=None: FalschesLlm(schema)
ocr_modul.texterkennung = falsche_texterkennung
ECHTES_PRUEFE = guardrail_modul.pruefe


def pruefe(name: str, ok: bool, detail: str = "") -> int:
    print(f"  {'✓' if ok else '✗'} {name}" + (f": {detail}" if detail else ""))
    return 0 if ok else 1


def starte(fall: str) -> AppTest:
    FALL["id"] = fall
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    at.selectbox[1].set_value(fall)            # [0] = Sprache, [1] = Testbrief
    at.button(key="los_beispiel").click().run()
    return at


def texte(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown) + "\n".join(c.value for c in at.caption)


def fall_zahlungsbefehl() -> int:
    print("03 Zahlungsbefehl ohne Zustelldatum")
    at = starte("03_zahlungsbefehl_de_vertreter_ohne_zustelldatum")
    f = pruefe("Kein Fehler", not at.exception and not at.error,
               str([e.value for e in at.exception] + [e.value for e in at.error])[:300])
    f += pruefe("Frage nach Zustelldatum", any("erhalten" in m.value for m in at.markdown)
                and len(at.date_input) == 1)
    at.checkbox[0].uncheck()
    from datetime import date
    at.date_input[0].set_value(date(2026, 11, 18))
    at.button[0].click().run()
    t = texte(at)
    f += pruefe("Fristen 30.11. und 08.12.", "bis 30.11.2026" in t and "bis 08.12.2026" in t)
    f += pruefe("Zustelldatum mit Quelle", "Zugestellt am 18.11.2026 (Ihre Angabe)" in t)
    f += pruefe("Erklärung + Entwurf", "Testerklärung" in t and len(at.expander) == 1)
    knoepfe = [b.label for b in at.button]
    f += pruefe("Bestätigungsknöpfe", "Ja, in den Kalender" in knoepfe, str(knoepfe))
    next(b for b in at.button if b.label == "Ja, in den Kalender").click().run()
    f += pruefe("Kalender bereit", any("Kalender" in s.value for s in at.success),
                str([s.value for s in at.success]))
    f += pruefe("Neuer Brief möglich", any(b.label == "Neuen Brief erklären" for b in at.button))
    f += pruefe("Kein Fehler am Ende", not at.exception and not at.error)
    return f


def fall_unbekannt() -> int:
    print("37 Bussenverfügung (unbekannt, keine Frist)")
    at = starte("37_bussenverfuegung_de")
    t = texte(at)
    return (pruefe("Kein Fehler", not at.exception and not at.error)
            + pruefe("Kein Fristenkasten, keine Bestätigung",
                     "**Fristen**" not in t and not any("Ja," in b.label for b in at.button))
            + pruefe("Erklärung da", "Testerklärung" in t))


def fall_fallback() -> int:
    print("26 Mahnung mit Guardrail am Limit (Fallback)")
    guardrail_modul.pruefe = lambda state, mit_llm=None: GuardrailErgebnis(
        bestanden=False, zurueck_zu="erklaerung",
        verstoesse=[Verstoss(regel="erfundene_fakten", betrifft="erklaerung", detail="Test")])
    try:
        at = starte("26_mahnung_de_stufe2")
    finally:
        guardrail_modul.pruefe = ECHTES_PRUEFE
    t = texte(at)
    return (pruefe("Kein Fehler", not at.exception and not at.error)
            + pruefe("Hinweis Fallback", any("nicht automatisch geprüft" in i.value for i in at.info))
            + pruefe("Kein LLM-Text, Schritte der Vorlage", "Testerklärung" not in t
                     and "Lesen Sie den Brief selbst" in t)
            + pruefe("Prototyp-Hinweis als Fussnote", any("FHNW" in c.value for c in at.caption))
            + pruefe("Fristen bleiben", "bis 06.11.2026" in t))


if __name__ == "__main__":
    assert (DATEN / "03_zahlungsbefehl_de_vertreter_ohne_zustelldatum").exists()
    fehler = fall_zahlungsbefehl() + fall_unbekannt() + fall_fallback()
    print("Alle Tests bestanden" if fehler == 0 else f"{fehler} Fehler")
    sys.exit(1 if fehler else 0)
