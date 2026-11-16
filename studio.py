"""Einstieg für LangGraph Studio (Graph anzeigen und ausprobieren in LangSmith).

    pip install "langgraph-cli[inmem]"
    langgraph dev --tunnel --no-reload --allow-blocking   (Details im README)

Öffnet https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024 im Browser.
Ohne eigenen Checkpointer: Den stellt der Studio-Server (Threads, Interrupts).
Konfiguration in langgraph.json.
"""

from graph import baue_builder

graph = baue_builder().compile()
