"""Neuer Fall live: Zahlungsbefehl in den Weihnachts-Betreibungsferien zugestellt (braucht .env)."""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mocks import mock_bis                 # noqa: E402
from nodes.erklaerung import erklaerung    # noqa: E402
from nodes.fristen import fristen          # noqa: E402
from nodes.guardrail import guardrail      # noqa: E402

state = mock_bis("zahlungsbefehl", "analyse")
state["zustelldatum"] = date(2026, 12, 22)   # mitten in den Ferien (18.12.-01.01.)
state["extraktion"] = state["extraktion"].model_copy(update={"briefdatum": date(2026, 12, 17)})
state.update(fristen(state))
for f in state["fristen"]:
    print(f"{f.art}: {f.datum:%d.%m.%Y} ab {f.ausgangsdatum:%d.%m.%Y} {f.hinweise}")
state.update(erklaerung(state))
print("\n" + state["erklaerung"].text)
for s in state["erklaerung"].naechste_schritte: print("  •", s)
g = guardrail(state)["guardrail"]
print("\nGuardrail:", "bestanden" if g.bestanden else [v.detail for v in g.verstoesse])