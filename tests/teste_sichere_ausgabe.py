"""Fallback bei Guardrail-Limit testen (nodes/sichere_ausgabe.py), ohne LLM und ohne Netz.

1. Vorlage: Für alle 45 gespeicherten Fälle die Fallback-Erklärung bauen. Der Guardrail
   (deterministische Checks) darf an ihr nichts beanstanden: Sie enthält nur belegte Daten
   und Beträge, keine Personendaten, und ist in der verlangten Sprache.
2. Ersetzen: Nur der beanstandete Text wird ersetzt bzw. weggelassen.
3. Graph: Guardrail schlägt immer an -> nach 2 Versuchen sichere_ausgabe -> Bestätigung.

    python tests/teste_sichere_ausgabe.py        # -v: Fallback-Texte anzeigen
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

# Falsche Adresse: kein Aufruf darf aus Versehen beim echten Proxy landen
os.environ.update(LLM_MODEL="test", LLM_BASE_URL="http://localhost:9/v1", LLM_API_KEY="test",
                  GUARDRAIL_LLM="0")

import nodes.erklaerung as erklaer_modul  # noqa: E402
import nodes.guardrail as guardrail_modul  # noqa: E402
from graph import baue_graph  # noqa: E402
from mocks import mock_bis  # noqa: E402
from nodes.guardrail import deterministische_checks  # noqa: E402
from nodes.sichere_ausgabe import sichere_ausgabe, sichere_erklaerung  # noqa: E402
from prompts import HINWEIS_PROTOTYP  # noqa: E402
from state import Erklaerung, GuardrailErgebnis, Verstoss  # noqa: E402
from teste_guardrail import FAELLE, lade  # noqa: E402

VERBOSE = "-v" in sys.argv


def pruefe(name: str, ok: bool, detail: str = "") -> int:
    print(f"  {'✓' if ok else '✗'} {name}" + (f": {detail}" if detail else ""))
    return 0 if ok else 1


def limit(*betrifft: str) -> GuardrailErgebnis:
    return GuardrailErgebnis(
        bestanden=False, zurueck_zu="erklaerung",
        verstoesse=[Verstoss(regel="erfundene_fakten", betrifft=b, detail="Test") for b in betrifft])


def fall_vorlage_besteht_guardrail() -> int:
    print("Vorlage für alle gespeicherten Fälle")
    fehler = 0
    for datei in sorted(FAELLE.glob("*.json")):
        fall = datei.name[:2]
        s = lade(fall)
        if not s.get("text_lesbar", True):
            continue  # unlesbar: kein Graph bis zum Guardrail
        s["erklaerung"] = sichere_erklaerung(s)
        s.pop("antwortentwurf", None)
        v = deterministische_checks(s)
        if VERBOSE or v:
            print(f"\n--- {datei.stem} ---\n{s['erklaerung'].text}")
        if v:
            fehler += pruefe(datei.stem, False, "; ".join(f"{x.regel}: {x.detail}" for x in v))
    return fehler + pruefe("Guardrail beanstandet keine Vorlage", fehler == 0,
                           f"{len(list(FAELLE.glob('*.json')))} Fälle")


def fall_nur_beanstandetes_ersetzen() -> int:
    print("Nur der beanstandete Text")
    s = mock_bis("zahlungsbefehl", "antwort")
    erkl, entwurf = s["erklaerung"], s["antwortentwurf"]
    f = 0

    u = sichere_ausgabe({**s, "guardrail": limit("erklaerung")})
    f += pruefe("Erklärung beanstandet", u["erklaerung"] is not erkl
                and u["erklaerung_verworfen"] is erkl and "antwortentwurf" not in u
                and u["fallback"] == ["erklaerung"], "Vorlage, Entwurf bleibt")

    u = sichere_ausgabe({**s, "guardrail": limit("antwortentwurf")})
    f += pruefe("Antwortentwurf beanstandet", u["antwortentwurf"] is None
                and u["antwortentwurf_verworfen"] is entwurf
                and "erklaerung_verworfen" not in u
                and u["erklaerung"].text.startswith(erkl.text.split("\n")[0])
                and "Antwortentwurf" in u["erklaerung"].text,
                "Erklärung bleibt, Entwurf weg, Satz dazu")

    # Satz steht vor dem Prototyp-Hinweis, der bleibt am Schluss
    mit_hinweis = erkl.model_copy(update={"text": f"{erkl.text}\n\n{HINWEIS_PROTOTYP['de']}"})
    u = sichere_ausgabe({**s, "erklaerung": mit_hinweis, "guardrail": limit("antwortentwurf")})
    f += pruefe("Prototyp-Hinweis bleibt am Schluss",
                u["erklaerung"].text.endswith(HINWEIS_PROTOTYP["de"]))

    u = sichere_ausgabe({**s, "guardrail": limit("erklaerung", "antwortentwurf")})
    f += pruefe("Beide beanstandet", u["antwortentwurf"] is None
                and u["erklaerung_verworfen"] is erkl
                and u["fallback"] == ["antwortentwurf", "erklaerung"]
                and u["erklaerung"].text.endswith(HINWEIS_PROTOTYP["de"]))

    for sprache in ("fr", "it"):
        u = sichere_ausgabe({**s, "nutzersprache": sprache, "guardrail": limit("erklaerung")})
        f += pruefe(f"Sprache {sprache}", u["erklaerung"].sprache == sprache
                    and u["erklaerung"].text.endswith(HINWEIS_PROTOTYP[sprache]))
    return f


class ImmerGleicheErklaerung:
    def __call__(self, schema, model=None):
        return self

    def invoke(self, nachrichten):
        return Erklaerung(sprache="de", text="LLM-Erklärung mit Fehler.")


def fall_graph() -> int:
    print("Graph: Guardrail immer am Limit")
    echt_llm, echt_pruefe = erklaer_modul.strukturiert, guardrail_modul.pruefe
    try:
        erklaer_modul.strukturiert = ImmerGleicheErklaerung()
        guardrail_modul.pruefe = lambda state, mit_llm=None: limit("erklaerung")
        graph = baue_graph()
        config = {"configurable": {"thread_id": "limit"}}
        start = mock_bis("steuerveranlagung", "fristen")  # ohne Antwortentwurf-LLM:
        start["brieftyp"] = "mahnung"                     # Mahnung braucht keinen Entwurf
        graph.update_state(config, start, as_node="fristen")
        ende = graph.invoke(None, config, interrupt_before=["kalender"])
    finally:
        erklaer_modul.strukturiert, guardrail_modul.pruefe = echt_llm, echt_pruefe
    frage = ende.get("__interrupt__")
    ok = (ende["versuche"]["guardrail"] == 2 and ende["fallback"] == ["erklaerung"]
          and ende["erklaerung_verworfen"].text.startswith("LLM-Erklärung")
          and "nicht automatisch geprüft" in ende["erklaerung"].text
          and frage and frage[0].value["typ"] == "bestaetigung"
          and not ende.get("abbruch_grund"))
    return pruefe("2 Versuche -> sichere_ausgabe -> Bestätigungsfrage", bool(ok),
                  f"Versuche {ende['versuche'].get('guardrail')}, fallback {ende.get('fallback')}")


if __name__ == "__main__":
    fehler = fall_vorlage_besteht_guardrail() + fall_nur_beanstandetes_ersetzen() + fall_graph()
    print("Alle Tests bestanden" if fehler == 0 else f"{fehler} Fehler")
    sys.exit(1 if fehler else 0)
