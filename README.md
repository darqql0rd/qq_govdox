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
| `mcp_kalender/` | Kalender-MCP-Server: trägt bestätigte Fristen in den Google Kalender ein (siehe unten) |
| `app.py` | Web-Oberfläche (Streamlit), siehe «Oberfläche» unten |
| `main.py` | Alle oder einzelne Testbriefe durch den Graphen schicken und mit `gold.json` vergleichen |

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

## Oberfläche

```bash
streamlit run app.py
```

Öffnet sich im Browser (http://localhost:8501). Brief hochladen (PDF oder Fotos, eine Datei
pro Seite) oder einen der 45 Testbriefe wählen. Die UI stellt die Fragen des Graphen
(Zustelldatum, Bestätigung) als Eingabefelder und bietet die Fristen als `.ics`-Datei an.
Fristen stehen oben in einem eigenen Kasten, weil sie aus dem Fristenrechner kommen, nicht vom LLM.
Test ohne LLM: `python tests/teste_app.py`.

## Zuständigkeiten

| Person | Agent | Weitere Bausteine |
|---|---|---|
| Melvin | Antwort-Agent | LangGraph-Graph, Routing, Human-in-the-loop |
| Nayan | Analyse-Agent | Texterkennung/OCR, Kalender-MCP, Apertus-Vision-Test |
| Vendon | Erklär-Agent | Fristenrechner, State |
| Florian | Guardrail-Agent | Evaluation, Apertus-Vergleich, UI |

## Warum kein RAG

Ursprünglich geplant war RAG über offizielle Infoblätter. Wir haben bewusst darauf verzichtet:

- Das nötige Wissen ist klein und stabil (vier Brieftypen, ihre Rechtsmittel und Fristen) und
  steht direkt im Prompt.
- Fristen berechnet der Fristenrechner deterministisch in Python, nicht das LLM.
- Der Guardrail prüft jede Aussage gegen die Fakten im State (Extraktion, Fristen). Texte aus
  einem Retrieval liessen sich so nicht prüfen und wären eine zusätzliche Fehlerquelle.

## Kalender (Google Kalender über MCP)

Der Kalender-Node (`nodes/kalender.py`) startet den MCP-Server `mcp_kalender/server.py`
selbst und ruft dessen Tool `frist_eintragen` auf. Standard ist `KALENDER_KANAL=ics` in
`.env`: Dann entsteht nur eine `.ics`-Datei in `ausgabe/`, der echte Kalender bleibt leer.
Dasselbe passiert, wenn Google nicht erreichbar oder das Login abgelaufen ist.

Google einrichten (einmalig):

1. In der Google Cloud Console die Google Calendar API aktivieren und einen OAuth-Client
   vom Typ „Desktop-App“ erstellen, das JSON als `credentials.json` in den Repo-Ordner legen.
   Das eigene Google-Konto als Testnutzer eintragen.
2. In `.env`: `KALENDER_KANAL=google` und `GOOGLE_CALENDAR_ID=<Kalender-ID>`.
3. `python mcp_kalender/login.py` – Browser-Login, danach liegt `token.json` im Repo-Ordner.
   Im Google-Status „Testing“ läuft das Login nach 7 Tagen ab, dann nochmals ausführen.

`credentials.json` und `token.json` stehen in `.gitignore` und gehören nie ins Repo.
Tools von Hand testen: `mcp dev mcp_kalender/server.py` (MCP Inspector).

## Datenschutz

Alle Briefe sind synthetisch; Personen, Ämter, Adressen und IBANs sind erfunden.
Keine echten Briefe ins Repo, Zugangsdaten nur in `.env`.
