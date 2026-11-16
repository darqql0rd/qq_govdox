"""Zentrale LLM-Anbindung über den LiteLLM-Proxy der FHNW.

Alle Nodes holen ihr Modell hier. So wechselt man das Modell an einer Stelle
(z. B. für den Apertus-Vergleich) und nicht in jedem Node.

Test der Verbindung:  python llm.py
"""

import os

import openai
from dotenv import load_dotenv
from langchain_core.exceptions import OutputParserException
from langchain_openai import ChatOpenAI
from langgraph.types import RetryPolicy
from pydantic import ValidationError

load_dotenv()  # liest .env im Repo-Root (Keys, Modellname, Tracing)

# Vorübergehende Fehler des LiteLLM-Proxys: nochmals versuchen lohnt sich.
# Ein falscher Key oder ein Bug bleiben Fehler (kein Retry). Kaputte strukturierte
# Ausgabe (STRUKTURFEHLER) wird dagegen wiederholt, siehe unten.
# langchain_openai.OpenAIConnectionError ist eine Unterklasse von APIConnectionError.
VORUEBERGEHEND = (
    openai.APIConnectionError,   # Proxy nicht erreichbar ("Connection error.")
    openai.APITimeoutError,
    openai.RateLimitError,       # 429
    openai.InternalServerError,  # 5xx
)

# Kaputte strukturierte Ausgabe: Das Modell liefert JSON, das nicht zum Schema passt
# oder gar keinen Tool-Aufruf. Läufe 09.11., Briefe 24 und 35: ValidationError in der Analyse,
# einmal fehlte "extraktion", zweimal stand darin XML statt JSON ('<parameter name="absen...').
# Ein neuer Aufruf liefert meist eine gültige Antwort (Haiku läuft mit temperature=1).
STRUKTURFEHLER = (ValidationError, OutputParserException)

# Stufe 1: der OpenAI-Client wiederholt selbst, aber nur mit kurzen Pausen (< 10 s).
LLM_TIMEOUT_S = 120  # grosszügig: Apertus-70B braucht für lange Antworten teils deutlich länger als Haiku
LLM_MAX_RETRIES = 3

# Stufe 2: LangGraph wiederholt den ganzen Node mit längeren Pausen (ca. 5 s, 10 s, 20 s).
# Nur für Nodes mit LLM-Aufruf und ohne interrupt() verwenden (siehe graph.py).
LLM_RETRY = RetryPolicy(
    max_attempts=4,
    initial_interval=5.0,
    backoff_factor=2.0,
    retry_on=VORUEBERGEHEND + STRUKTURFEHLER,
)


def get_llm(model: str | None = None) -> ChatOpenAI:
    """Chat-Modell über den OpenAI-kompatiblen LiteLLM-Endpunkt.

    Temperatur nur senden, wenn LLM_TEMPERATURE in .env gesetzt ist. Neuere Modelle
    (Claude Haiku 5.5, GPT-5) akzeptieren nur ihren Standardwert. Für Apertus und
    andere offene Modelle für reproduzierbare Ergebnisse LLM_TEMPERATURE=0 setzen.
    """
    extra = {}
    if os.getenv("LLM_TEMPERATURE"):
        extra["temperature"] = float(os.environ["LLM_TEMPERATURE"])
    return ChatOpenAI(
        model=model or os.environ["LLM_MODEL"],
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=LLM_TIMEOUT_S,
        max_retries=LLM_MAX_RETRIES,
        **extra,
    )


def strukturiert(schema, model: str | None = None):
    """LLM, das garantiert ein Pydantic-Objekt zurückgibt (SW5, Folie 17).

    method="function_calling" funktioniert mit fast allen Modellen hinter LiteLLM.
    Unterstützt das Modell JSON-Schema-Ausgabe, kann man in .env
    STRUCTURED_METHOD=json_schema setzen.
    """
    methode = os.getenv("STRUCTURED_METHOD", "function_calling")
    return get_llm(model).with_structured_output(schema, method=methode)


if __name__ == "__main__":
    from openai import OpenAI

    client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
    print("Verfügbare Modelle:")
    for m in client.models.list():
        print("  ", m.id)
    print("\nTestantwort von", os.environ["LLM_MODEL"], ":")
    print(get_llm().invoke("Antworte mit genau einem Wort: Funktioniert die Verbindung?").content)
