"""Zentrale LLM-Anbindung über den LiteLLM-Proxy der FHNW.

Alle Nodes holen ihr Modell hier. So wechselt man das Modell an einer Stelle
(z. B. für den Apertus-Vergleich) und nicht in jedem Node.

Test der Verbindung:  python llm.py
"""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()  # liest .env im Repo-Root (Keys, Modellname, Tracing)


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
