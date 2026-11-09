"""Automatisches Wiederholen bei Verbindungsfehlern testen (RetryPolicy in graph.py).

Läuft im echten Graphen ab dem Node "erklaerung" (Mock-State nach "fristen").
Das LLM wird ersetzt, es braucht also weder Key noch Netz. Die Pausen sind die echten
(5 s, 10 s, 20 s), deshalb dauert der Test knapp eine Minute.

    python tests/teste_retry.py          # ohne Netz, ca. 1 Minute
    python tests/teste_retry.py --netz   # zusätzlich: echter Aufruf an eine falsche Adresse
                                         # (Client- und Node-Retries, dauert ca. 1 Minute)
"""

import os
import sys
import time
from pathlib import Path

import httpx
import openai

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Falsche Adresse: kein Aufruf darf aus Versehen beim echten Proxy landen
os.environ.update(LLM_MODEL="test", LLM_BASE_URL="http://localhost:9/v1", LLM_API_KEY="test")

import nodes.erklaerung as erklaer_modul  # noqa: E402
from graph import baue_graph  # noqa: E402
from llm import LLM_RETRY, VORUEBERGEHEND  # noqa: E402
from mocks import mock_bis  # noqa: E402
from state import Erklaerung  # noqa: E402

ECHTES_STRUKTURIERT = erklaer_modul.strukturiert
VERBINDUNGSFEHLER = openai.APIConnectionError(request=httpx.Request("POST", "http://localhost:9"))


class FalschesLlm:
    """Wirft zuerst `fehler_anzahl` Mal `fehler`, liefert dann eine Erklärung."""

    def __init__(self, fehler, fehler_anzahl):
        self.fehler, self.rest, self.aufrufe = fehler, fehler_anzahl, 0

    def __call__(self, schema, model=None):  # ersetzt strukturiert(schema)
        return self

    def invoke(self, nachrichten):
        self.aufrufe += 1
        if self.rest > 0:
            self.rest -= 1
            raise self.fehler
        return Erklaerung(sprache="de", text="Testerklärung")


def lauf_ab_erklaerung(thread: str):
    """Echten Graphen ab "erklaerung" laufen lassen, vor "antwort" anhalten."""
    graph = baue_graph()
    config = {"configurable": {"thread_id": thread}}
    graph.update_state(config, mock_bis("zahlungsbefehl", "fristen"), as_node="fristen")
    start = time.monotonic()
    try:
        ende = graph.invoke(None, config, interrupt_before=["antwort", "guardrail"])
        return ende, None, time.monotonic() - start
    except Exception as fehler:
        return None, fehler, time.monotonic() - start


def pruefe(name: str, ok: bool, detail: str) -> int:
    print(f"  {'✓' if ok else '✗'} {name}: {detail}")
    return 0 if ok else 1


def fall_konfiguration() -> int:
    knoten = baue_graph().builder.nodes
    mit = {n for n, k in knoten.items() if k.retry_policy}
    erwartet = {"analyse", "erklaerung", "antwort", "guardrail"}
    return pruefe("Konfiguration", mit == erwartet,
                  f"RetryPolicy bei {sorted(mit)} (ohne interrupt-Nodes, OCR, Fristen)")


def fall_erholt_sich() -> int:
    llm = FalschesLlm(VERBINDUNGSFEHLER, fehler_anzahl=2)
    erklaer_modul.strukturiert = llm
    ende, fehler, dauer = lauf_ab_erklaerung("erholt")
    ok = fehler is None and ende.get("erklaerung") is not None and llm.aufrufe == 3
    return pruefe("Proxy 2× weg, dann wieder da", ok,
                  f"{llm.aufrufe} Aufrufe, {dauer:.0f} s, Erklärung vorhanden: {ende is not None}")


def fall_bleibt_weg() -> int:
    llm = FalschesLlm(VERBINDUNGSFEHLER, fehler_anzahl=99)
    erklaer_modul.strukturiert = llm
    _, fehler, dauer = lauf_ab_erklaerung("weg")
    ok = isinstance(fehler, VORUEBERGEHEND) and llm.aufrufe == LLM_RETRY.max_attempts
    return pruefe("Proxy bleibt weg", ok,
                  f"nach {llm.aufrufe} Versuchen und {dauer:.0f} s: {type(fehler).__name__}")


def fall_kein_retry_bei_bug() -> int:
    llm = FalschesLlm(ValueError("falsches Schema"), fehler_anzahl=99)
    erklaer_modul.strukturiert = llm
    _, fehler, dauer = lauf_ab_erklaerung("bug")
    ok = isinstance(fehler, ValueError) and llm.aufrufe == 1
    return pruefe("Anderer Fehler (kein Retry)", ok, f"{llm.aufrufe} Aufruf, {dauer:.1f} s")


def fall_antwort_reicht_weiter() -> int:
    """antwort.py fängt sonst jeden Fehler ab; Verbindungsfehler muss es weiterwerfen."""
    import nodes.antwort as antwort_modul
    echt = antwort_modul.strukturiert
    state = mock_bis("zahlungsbefehl", "erklaerung")
    try:
        antwort_modul.strukturiert = FalschesLlm(VERBINDUNGSFEHLER, fehler_anzahl=1)
        try:
            antwort_modul.antwort(state)
            weiter = False
        except VORUEBERGEHEND:
            weiter = True
        antwort_modul.strukturiert = FalschesLlm(ValueError("Bug"), fehler_anzahl=1)
        sonst_none = antwort_modul.antwort(state) == {"antwortentwurf": None}
    finally:
        antwort_modul.strukturiert = echt
    return pruefe("Antwort-Agent", weiter and sonst_none,
                  "Verbindungsfehler -> weiterwerfen, anderer Fehler -> kein Entwurf")


def fall_netz() -> int:
    erklaer_modul.strukturiert = ECHTES_STRUKTURIERT
    _, fehler, dauer = lauf_ab_erklaerung("netz")
    ok = isinstance(fehler, VORUEBERGEHEND)
    return pruefe("Echter Aufruf an falsche Adresse", ok,
                  f"{type(fehler).__name__} nach {dauer:.0f} s (Client- + Node-Retries)")


if __name__ == "__main__":
    fehler = (fall_konfiguration() + fall_kein_retry_bei_bug() + fall_antwort_reicht_weiter()
              + fall_erholt_sich() + fall_bleibt_weg())
    if "--netz" in sys.argv:
        fehler += fall_netz()
    erklaer_modul.strukturiert = ECHTES_STRUKTURIERT
    print("Alle Tests bestanden" if fehler == 0 else f"{fehler} Fehler")
    sys.exit(1 if fehler else 0)
