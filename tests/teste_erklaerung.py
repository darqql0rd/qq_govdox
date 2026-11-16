"""Erklär-Node testen, ohne LLM: fester Prototyp-Hinweis aus Python (HINWEIS_PROTOTYP).

1. Der Hinweis steht genau einmal am Schluss, in der verlangten Sprache (DE/FR/IT),
   auch beim Neuversuch, wenn das LLM die bisherige Erklärung samt Hinweis übernimmt.
2. Er löst im Guardrail keinen neuen Alarm aus: alle 45 gespeicherten Fälle mit und
   ohne Hinweis prüfen, die Meldungen müssen gleich bleiben.

    python tests/teste_erklaerung.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.update(LLM_MODEL="test", LLM_BASE_URL="http://localhost:9/v1", LLM_API_KEY="test")

import nodes.erklaerung as erklaer_modul  # noqa: E402
from mocks import mock_bis  # noqa: E402
from nodes.guardrail import deterministische_checks  # noqa: E402
from prompts import HINWEIS_PROTOTYP  # noqa: E402
from state import Erklaerung  # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from teste_guardrail import FAELLE, lade  # noqa: E402

LLM_TEXT = {"de": "Sie haben einen Zahlungsbefehl erhalten.",
            "fr": "Vous avez reçu un commandement de payer.",
            "it": "Ha ricevuto un precetto esecutivo."}


class FalschesLlm:
    def __init__(self, sprache):
        self.sprache = sprache

    def __call__(self, schema, model=None):
        return self

    def invoke(self, nachrichten):
        return Erklaerung(sprache=self.sprache, text=LLM_TEXT[self.sprache] + "\n")


def pruefe(name: str, ok: bool, detail: str = "") -> int:
    print(f"  {'✓' if ok else '✗'} {name}{': ' + detail if detail else ''}")
    return 0 if ok else 1


def teste_hinweis() -> int:
    fehler = 0
    echt = erklaer_modul.strukturiert
    try:
        for sprache in ("de", "fr", "it"):
            erklaer_modul.strukturiert = FalschesLlm(sprache)
            state = mock_bis("zahlungsbefehl", "fristen")
            state["nutzersprache"] = sprache
            text = erklaer_modul.erklaerung(state)["erklaerung"].text
            hinweis = HINWEIS_PROTOTYP[sprache]
            ok = (text.startswith(LLM_TEXT[sprache]) and text.endswith(hinweis)
                  and text.count("FHNW") == 1)
            fehler += pruefe(f"Hinweis auf {sprache.upper()}", ok, repr(text[-60:]))
    finally:
        erklaer_modul.strukturiert = echt
    return fehler


class UebernimmtBisherigeErklaerung:
    """Wie Haiku am 16.11.: gibt beim Neuversuch den Text samt Hinweis zurück."""

    def __call__(self, schema, model=None):
        return self

    def invoke(self, nachrichten):
        import json
        fakten = json.loads(nachrichten[-1].content)
        self.gesehen = fakten.get("bisherige_erklaerung", {}).get("text", "")
        return Erklaerung(sprache="de", text="Korrigiert. " + self.gesehen
                          + "\n\n" + HINWEIS_PROTOTYP["de"])


def teste_hinweis_neuversuch() -> int:
    from state import GuardrailErgebnis, Verstoss
    echt = erklaer_modul.strukturiert
    llm = UebernimmtBisherigeErklaerung()
    try:
        erklaer_modul.strukturiert = llm
        state = mock_bis("zahlungsbefehl", "fristen")
        state["nutzersprache"] = "de"
        state["erklaerung"] = Erklaerung(
            sprache="de", text=f"Alter Text.\n\n{HINWEIS_PROTOTYP['de']}")
        state["guardrail"] = GuardrailErgebnis(bestanden=False, zurueck_zu="erklaerung", verstoesse=[
            Verstoss(regel="erfundene_fakten", betrifft="erklaerung", detail="Test")])
        text = erklaer_modul.erklaerung(state)["erklaerung"].text
    finally:
        erklaer_modul.strukturiert = echt
    ok = ("FHNW" not in llm.gesehen and text.count("FHNW") == 1
          and text.endswith(HINWEIS_PROTOTYP["de"]))
    return pruefe("Neuversuch: Hinweis genau einmal (Lauf 16.11.)", ok,
                  f"{text.count('FHNW')}× im Text, ans LLM {'mit' if 'FHNW' in llm.gesehen else 'ohne'} Hinweis")


def teste_guardrail_unveraendert() -> int:
    abweichend = []
    for datei in sorted(FAELLE.glob("*.json")):
        state = lade(datei.stem[:2])
        if not state.get("erklaerung"):
            continue
        vorher = {(v.regel, v.detail) for v in deterministische_checks(state)}
        sprache = state.get("nutzersprache") or state.get("briefsprache") or "de"
        e = state["erklaerung"]
        state["erklaerung"] = e.model_copy(update={"text": f"{e.text}\n\n{HINWEIS_PROTOTYP[sprache]}"})
        nachher = {(v.regel, v.detail) for v in deterministische_checks(state)}
        if vorher != nachher:
            abweichend.append(f"{datei.stem}: neu {sorted(nachher - vorher)}")
    for a in abweichend:
        print(f"      {a}")
    return pruefe("Guardrail: Hinweis löst keinen neuen Alarm aus (45 Fälle)", not abweichend)


if __name__ == "__main__":
    total = teste_hinweis() + teste_hinweis_neuversuch() + teste_guardrail_unveraendert()
    print("Alle Tests bestanden" if total == 0 else f"{total} Fehler")
    sys.exit(1 if total else 0)
