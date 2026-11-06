"""Testfälle für den Guardrail erzeugen (Owner: Florian).

Schickt Briefe durch den heutigen Graphen (Analyse -> Fristen -> Erklärung) und
speichert den End-State pro Brief als JSON in tests/guardrail_faelle/.
Diese Fälle sind die Positivbeispiele für den Guardrail.

    python speichere_faelle.py            # alle 45 Briefe
    python speichere_faelle.py 01 26      # nur ausgewählte
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from graph import baue_graph       # noqa: E402
from main import EINGABE           # noqa: E402
from mocks import aus_gold, fall_ids  # noqa: E402

ZIEL = Path("tests/guardrail_faelle")


def als_json(objekt):
    """Pydantic-Modelle und Daten in JSON-taugliche Werte umwandeln."""
    if hasattr(objekt, "model_dump"):
        return objekt.model_dump(mode="json")
    return str(objekt)


def main(muster: list[str]):
    ZIEL.mkdir(parents=True, exist_ok=True)
    graph = baue_graph()
    faelle = [f for f in fall_ids() if not muster or any(f.startswith(m) or m in f for m in muster)]
    for fall in faelle:
        try:
            voll = aus_gold(fall, "pdf")
            start = {k: v for k, v in voll.items() if k in EINGABE}
            if voll.get("zustelldatum_quelle") == "nutzer":
                start["zustelldatum"] = voll["zustelldatum"]
                start["zustelldatum_quelle"] = "nutzer"
            ende = graph.invoke(start, config={"run_name": f"guardrail-fall-{fall}",
                                               "tags": ["guardrail-testdaten"]})
            datei = ZIEL / f"{fall}.json"
            datei.write_text(json.dumps(ende, default=als_json, ensure_ascii=False, indent=2),
                             encoding="utf-8")
            print(f"✓ {fall}")
        except Exception as fehler:
            print(f"✗ {fall}: {type(fehler).__name__}: {str(fehler)[:200]}")
    print(f"\nGespeichert in {ZIEL.resolve()}")


if __name__ == "__main__":
    main(sys.argv[1:])
