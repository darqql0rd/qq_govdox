# qq_govdox – Behördenbrief-Erklärer

Gruppenarbeit im Modul Generative KI (FHNW, HS 2026). Ein LLM-Agent auf Basis von LangGraph:
Man fotografiert einen Schweizer Behördenbrief (Zahlungsbefehl, Steuerveranlagung,
Krankenkassen-Prämie, Mahnung), der Agent erklärt ihn in einfacher Sprache (DE/FR/IT),
berechnet Fristen deterministisch, entwirft eine Antwort und trägt die Fristen nach
Bestätigung in den Kalender ein.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `state.py` | State-Schema des Graphen (Vertrag zwischen den Nodes). Owner: Melvin, Änderungen per Pull Request |
| `mocks.py` | Handgeschriebene Mock-States und `aus_gold()` zum Laden der Testbriefe |
| `notebooks/00_state_und_mocks.ipynb` | Übersicht: Schema, Mocks, Datensatz, Graph-Skelett mit Dummy-Nodes |
| `daten/briefe/` | 45 synthetische Testbriefe mit PDF, Scan, Handyfoto, Textebene und Gold-Label |
| `datengenerator/` | Skripte, mit denen die Testbriefe erzeugt werden (siehe dortiges README) |

## Loslegen

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; unter Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Dann `notebooks/00_state_und_mocks.ipynb` öffnen und alle Zellen ausführen.

Für den eigenen Node:

```python
from mocks import mock_bis, aus_gold
state = mock_bis("zahlungsbefehl", "fristen")                 # handgeschriebener Mock
state = aus_gold("01_zahlungsbefehl_de_wochenende", "foto")   # Fall aus dem Datensatz
```

## Zuständigkeiten

| Person | Agent | Weitere Bausteine |
|---|---|---|
| Melvin | Antwort-Agent | LangGraph-Graph, State, Routing, Human-in-the-loop, Kalender-MCP |
| Nayan | Analyse-Agent | Texterkennung/OCR, Apertus-Vision-Test |
| Vendon | Erklär-Agent | RAG über Infoblätter, Fristenrechner |
| Florian | Guardrail-Agent | Evaluation, Apertus-Vergleich, UI |

## Datenschutz

Alle Briefe sind synthetisch; Personen, Ämter, Adressen und IBANs sind erfunden.
Keine echten Briefe ins Repo, Zugangsdaten nur in `.env`.
