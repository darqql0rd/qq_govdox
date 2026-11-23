# Projektbericht QQ Govdox

Gruppenarbeit im Modul Generative KI, FHNW, HS 2026. Florian (`darqql0rd`), Melvin
(`GingFreecssQQ`), Nayan (`Tayo0o0`), Vendon (`Vendoni`). Stand: 23.11.2026.

Dieser Bericht fasst das Projekt als Ganzes zusammen. Details, Befehle und Zahlen stehen in den
verlinkten Dateien; das [README](../README.md) erklärt, wie man den Agenten startet.

## Inhalt

1. [Problemstellung](#1-problemstellung)
2. [Lösungsansatz](#2-lösungsansatz)
3. [Architektur](#3-architektur)
4. [Entscheide und verworfene Alternativen](#4-entscheide-und-verworfene-alternativen)
5. [Daten](#5-daten)
6. [Evaluation](#6-evaluation)
7. [Grenzen](#7-grenzen)
8. [Nächste Schritte](#8-nächste-schritte)
9. [Einsatz von KI-Werkzeugen](#9-einsatz-von-ki-werkzeugen)

## 1. Problemstellung

Behördenbriefe sind juristisch formuliert, und in der Schweiz kommen sie auf Deutsch,
Französisch oder Italienisch. Das Folgenreichste an ihnen sind die Fristen: Gegen einen
Zahlungsbefehl hat man 10 Tage für den Rechtsvorschlag (SchKG Art. 74), gegen eine
Steuerveranlagung 30 Tage für die Einsprache (DBG Art. 132). Wer die Frist verpasst, verliert das
Rechtsmittel. Die Frist beginnt mit der Zustellung, nicht mit dem Briefdatum, und sie verschiebt
sich bei Wochenenden, Feiertagen und Betreibungsferien.

**Ziel:** Man fotografiert einen Brief und erhält eine Erklärung in einfacher Sprache, die
korrekten Fristen in seinem Kalender und einen Entwurf für die Antwort.

**Umfang:** vier Brieftypen, nämlich Zahlungsbefehl, Steuerveranlagung, Prämienmitteilung der
Krankenkasse und Mahnung. Andere Briefe werden als «unbekannt» erkannt und nur allgemein erklärt,
ohne Fristen.

## 2. Lösungsansatz

Grundsatz: **Das Sprachmodell liest und formuliert, Python rechnet und prüft.**

| Aufgabe | Wer | Warum |
|---|---|---|
| Text aus Foto oder PDF | docTR lokal, `pypdf` | keine Personendaten an einen Cloud-Dienst |
| Brieftyp erkennen, Beträge und Daten herausziehen | LLM mit strukturierter Ausgabe | Verstehen von Text ist die Stärke des LLM |
| Fristen berechnen | Python | ein LLM rechnet mit Daten nicht zuverlässig und nicht reproduzierbar |
| Erklärung und Antwortentwurf | LLM | Formulieren in einfacher Sprache, DE/FR/IT |
| Ausgabe prüfen, Rückfallebene | Python plus LLM-Check | Fehler des Modells abfangen, bevor die Person sie sieht |
| Zustelldatum, Bestätigung | Mensch (`interrupt()`) | Eingaben, die nur die Person kennt oder verantworten muss |
| Kalendereintrag | eigener MCP-Server | Werkzeug mit minimalen Rechten |

## 3. Architektur

LangGraph-`StateGraph` mit 10 Nodes ([`graph.py`](../graph.py), Diagramm im README).

| Node | Datei | Typ | Verantwortlich | Aufgabe |
|---|---|---|---|---|
| OCR | `nodes/ocr.py` | Python (docTR) | Nayan | PDF-Text direkt, Fotos mit docTR; Konfidenz < 0.75 gilt als unlesbar → neues Foto, nach 2 Versuchen Abbruch |
| Analyse | `nodes/analyse.py` | LLM | Nayan | Brieftyp, Absender, Beträge, Daten, Referenzen, `injection_verdacht`; Vorzeichen von Guthaben in Python korrigiert |
| Zustelldatum erfragen | `nodes/zustelldatum_erfragen.py` | Mensch | Melvin | nur wenn das Datum im Brief fehlt; «weiss nicht» → Briefdatum als Schätzung (Frist eher zu früh) |
| Fristen | `nodes/fristen.py`, `fristenrechner.py` | Python | Vendon | Fristen nach SchKG, ZPO, DBG, KVG, siehe [`fristen_rechtsgrundlagen.md`](fristen_rechtsgrundlagen.md) |
| Erklärung | `nodes/erklaerung.py` | LLM | Vendon | einfache Sprache, bekommt nur extrahierte Felder und Fristen, nie den Brieftext |
| Antwort | `nodes/antwort.py` | LLM | Melvin | Entwurf für Rechtsvorschlag, Einsprache oder Kündigung; Art, Empfänger und Platzhalter legt Python fest |
| Guardrail | `nodes/guardrail.py` | Python + LLM | Florian | prüft Erklärung und Entwurf, gezielter Rücksprung bei Verstoss |
| Sichere Ausgabe | `nodes/sichere_ausgabe.py` | Python | Florian | nach 2 beanstandeten Versuchen: Vorlage aus geprüften Fakten, fehlerhafter Entwurf fällt weg |
| Bestätigung | `nodes/bestaetigung.py` | Mensch | Melvin | Fristen bestätigen, erst dann Kalender |
| Kalender | `nodes/kalender.py`, `mcp_kalender/` | MCP-Tool | Nayan | Google Kalender über eigenen MCP-Server, sonst `.ics` |

**State als Vertrag** ([`state.py`](../state.py), Vendon): ein `TypedDict`, dessen Teilobjekte
Pydantic-Modelle sind. Die Agenten verwenden sie direkt mit `with_structured_output`; die
`description` jedes Felds ist Teil des Prompts. `FELDER_PRO_NODE` legt fest, welcher Node welche
Felder schreibt. Mit diesem Vertrag und den Mock-States (`mocks.py`) konnten wir zu viert parallel
an den Nodes arbeiten.

**Routing:** Bedingte Kanten für «unlesbar», «Brieftyp unbekannt» (keine Fristen, kein Entwurf),
«Zustelldatum fehlt», «Guardrail-Verstoss» (Rücksprung zur Erklärung oder zum Entwurf) und
«Guardrail-Limit» (sichere Ausgabe). Ein Antwortentwurf entsteht nur bei Zahlungsbefehl,
Steuerveranlagung und Krankenkasse.

**Human in the loop:** `interrupt()` hält den Graphen an, der Checkpointer (`MemorySaver`)
speichert den State pro `thread_id` (ein Thread pro Brief), `Command(resume=…)` setzt an derselben
Stelle fort. Die Antwort der Person wandelt `datum.py` um, nicht das LLM.

**Robustheit:** Alle LLM-Nodes haben eine `RetryPolicy` (`llm.py`): Verbindungsfehler und
ungültige strukturierte Ausgaben (`ValidationError`, `OutputParserException`) werden bis zu
viermal wiederholt.

**Guardrail im Detail** (`nodes/guardrail.py`):

1. Deterministische Regeln in Python: Datum im Text, das weder berechnet noch im Brief steht, oder
   falscher Wochentag; Betrag, der nicht belegt ist; Name oder Adresse der Person; falsche
   Rechtsaussagen (z. B. «muss beim Amt ankommen», obwohl die Postaufgabe genügt, SchKG Art. 32;
   ein Rechtsmittel, das zum Brieftyp nicht passt); falsche Sprache.
2. LLM-Check für das, was Regeln nicht erkennen: Rechtsberatung, erfundene Fakten, befolgte
   Injection. Gewertet werden nur eindeutige Befunde.

**Schutz gegen Prompt Injection** in mehreren Schichten: Der Brief steht im Analyse-Prompt
abgegrenzt als Daten; Erklär- und Antwort-Agent sehen den Brieftext nie; der Guardrail prüft auf
befolgte Anweisungen; vor dem Kalendereintrag bestätigt die Person.

**Oberflächen:** Streamlit (`app.py`), LangGraph Studio (`studio.py`), Kommandozeile mit
Evaluation (`main.py`).

## 4. Entscheide und verworfene Alternativen

| Entscheid | Begründung | Verworfene Alternative |
|---|---|---|
| Fristen in Python | Fristen sind das Folgenreichste; feste Regeln lassen sich exakt umsetzen und testen. Rechtsprüfung am 09.11., siehe [`fristen_rechtsgrundlagen.md`](fristen_rechtsgrundlagen.md) | Fristen vom LLM berechnen lassen: nicht reproduzierbar, Sonderfälle wie Betreibungsferien werden leicht übersehen |
| Nur landesweite Feiertage | Der Kanton ist unbekannt. Fehlende kantonale Feiertage machen eine Frist höchstens zu früh | Alle Feiertage zählen (alte Version): Frist konnte im Tessin oder Wallis zu spät sein |
| Erklär- und Antwort-Agent ohne Brieftext | Schutz gegen Prompt Injection über die Architektur | Nur auf die Erkennung im Prompt setzen: Der Hold-out zeigt, dass neue Formulierungen durchrutschen |
| Guardrail mit sicherer Ausgabe | Die Person bekommt auch im schlechtesten Fall ihre korrekten Fristen | Bei Verstoss abbrechen: Die Person stünde ohne Ergebnis da |
| Claude Haiku über den FHNW-Proxy | Klein und schnell (ca. 25 s pro Brief); zuverlässige strukturierte Ausgabe; gute Texte in DE/FR/IT; mehr braucht es nicht, weil Rechnen und Prüfen in Python liegen | Apertus als Hauptmodell: in unserer Pipeline 20/45, langsamer (48 statt 19 min für 45 Briefe). Grösseres Claude-Modell: nicht nötig, teurer |
| Kein RAG | Das Fachwissen ist klein und stabil (vier Brieftypen, ihre Rechtsmittel) und steht im Prompt. Fristen rechnet Python. Texte aus einem Retrieval könnte der Guardrail nicht gegen den State prüfen | RAG über offizielle Merkblätter (ursprünglich geplant, im November verworfen) |
| Eigener MCP-Server, Scope nur `calendar.events` | Minimale Rechte; austauschbar und ohne Agent testbar; `.ics`-Fallback | Googles offizieller Workspace-MCP (nur für Workspace-Konten); fremder Server `workspace-mcp` (Kalender und Gmail mit breiten Rechten); direkter API-Aufruf (einfacher, aber ohne das Modul-Thema MCP) |
| OCR lokal mit docTR | Fotos mit Personendaten bleiben auf dem Rechner. Mehrsprachiges PARSeq-Modell für ä, ö, é | Cloud-OCR (Datenschutz); Tesseract (liess sich unter macOS nicht installieren) |
| Fester Workflow statt frei verhandelnder Agenten | Für Behördenbriefe nachvollziehbar und prüfbar | Multi-Agent-System, in dem die Agenten den Ablauf selbst bestimmen |
| Synthetische Testbriefe | Keine echten Personendaten; Gold-Labels und gezielte Testfälle möglich | Echte, geschwärzte Briefe: zu wenige, Labels von Hand, Datenschutz |

## 5. Daten

Alle Briefe sind synthetisch und mit einem eigenen Generator erzeugt
([`datengenerator/`](../datengenerator/README.md)): Layout mit `reportlab`, Scan und Handyfoto mit
`opencv` (Perspektive, Schatten, Hintergrund, Rauschen), handschriftliche Zustelldaten, QR-Rechnungen,
Wasserzeichen.

- **45 Entwicklungsbriefe** ([`daten/briefe/`](../daten/briefe)): DE/FR/IT, je als PDF, Scan,
  Handyfoto, Textebene und `gold.json`.
- **20 Hold-out-Briefe** ([`daten/holdout/`](../daten/holdout/README.md)), erzeugt am 17.11.,
  nachdem die Pipeline eingefroren war.
- **Gezielte Testfälle:** Wochenende, Feiertag, Betreibungsferien, fehlendes Zustelldatum,
  Vertreter, Rückerstattung, Abweichung von der Deklaration, Prompt Injection, absichtlich
  unlesbare Fotos, Negativfälle ausserhalb des Umfangs (Busse, Konkursandrohung,
  Pfändungsankündigung, Abstimmungsunterlagen u. a.).
- **Gold-Label (Musterlösung):** Brieftyp, Extraktion, erwartete Fristen, Injection ja/nein. Die
  erwarteten Fristen stammen aus einer eigenen Fristenlogik des Generators
  (`datengenerator/fristen.py`), unabhängig vom Fristenrechner des Agenten. Sonst würde die
  Evaluation den Code gegen sich selbst prüfen.

## 6. Evaluation

**Methode:** `main.py` schickt Briefe durch den ganzen Graphen (Handyfoto mit OCR) und vergleicht
mit dem Gold-Label. Ein Brief ist **korrekt**, wenn Brieftyp, Fristen, Betrag und
Injection-Erkennung alle stimmen. Zweite Kennzahl: korrekt **und** vom Guardrail ohne Fallback
freigegeben. Die Antwort auf die Frage nach dem Zustelldatum kommt aus dem Gold-Label. Die
Textqualität wird nicht automatisch gemessen, sondern stichprobenweise gelesen.

**Ergebnisse** (Protokolle und Auswertungen in [`daten/laeufe/`](../daten/laeufe/README.md)):

| Datensatz | Modell | Läufe | korrekt | Anteil |
|---|---|---|---|---|
| Entwicklung, 45 Briefe | Claude Haiku | 3 | 42 / 42 / 41 | ≈ 93 % |
| Hold-out, 20 Briefe | Claude Haiku | 2 | 14 / 14 | 70 % |
| Entwicklung, 45 Briefe | Apertus v1.5 70B, `temperature=0` | 1 | 20 | 44 % |

Verlauf mit Haiku: 29/45 (04.11.) → 34–38 (09.11., Graph mit Guardrail) → 41–42 (16.11.).

**Befunde:**

- **Overfitting:** Prompts und Regeln wurden an den 45 Briefen verbessert. Auf neuen Briefen sinkt
  die Quote von 93 % auf 70 %. Weil der Hold-out aus demselben Generator stammt, ist 70 % eher eine
  obere Schranke für echte Briefe.
- **Fehler sind systematisch:** In allen Haiku-Läufen fallen dieselben Briefe durch (04, 13, 14;
  im Hold-out 47, 49, 60, 61, 62, 63). Nur welcher Brief am Guardrail-Limit landet, wechselt.
- **Der Guardrail prüft Konsistenz, nicht Richtigkeit:** Er vergleicht die Texte mit den Fakten im
  State. Ist schon die Analyse falsch, passt alles zusammen. Beispiel Hold-out 62: Eine
  Pfändungsankündigung wurde als Zahlungsbefehl erkannt und mit einer Frist erklärt, die längst
  vorbei war – freigegeben. Bei Apertus wurden so 23 falsche Ergebnisse freigegeben.
- **Injection: Schutz hält, Erkennung nicht:** Die Erkennung (`injection_verdacht`) versagt bei 04
  und 14 und bei beiden neu formulierten Injections im Hold-out (47, 60). In keinem Lauf folgt aber
  eine Ausgabe der Anweisung, weil Erklär- und Antwort-Agent den Brieftext nie sehen.
- **Das Lesen ist der Engpass:** handschriftliche Daten (04, 49), falsche Tabellenzeile beim Betrag
  (13, 63), unlesbares Foto mit Konfidenz knapp über der Schwelle (61). Kein Fristfehler kam aus
  der Fristberechnung selbst.
- **Apertus:** Der Vergleich ist nicht fair, weil Prompts und Regeln an Haiku entwickelt wurden. Er
  misst, wie gut ein Modell ohne Anpassung in die Pipeline passt. Typische Fehler: Datumsfelder mit
  ganzen Sätzen, Briefe ausserhalb des Umfangs als Zahlungsbefehl erkannt, erfundene
  Zahlungsfristen.

**Tests ohne LLM** ([`tests/`](../tests)): Fristenrechner gegen Gold-Briefe und Rechtsfälle,
Guardrail an 45 gespeicherten End-States, Nachbearbeitung der Analyse, Retry, sichere Ausgabe
und die Oberfläche (Streamlit AppTest).

## 7. Grenzen

- Nur synthetische Briefe aus einem Generator; auch der Hold-out ist «in-distribution».
- Der Guardrail prüft keine Fakten; eine falsche Analyse kann freigegeben werden.
- Die Injection-Erkennung ist an Muster gebunden und erkennt neue Formulierungen nicht.
- Kantonale Feiertage fehlen bewusst (Frist eher zu früh). Ostermontag und Pfingstmontag zählen,
  obwohl sie im Wallis nicht eindeutig gelten.
- Ein falsch gelesenes oder falsch eingegebenes Zustelldatum verschiebt die Fristen; die Rechnung
  selbst kann das nicht erkennen.
- Krankenkasse: Der Wechsel zu einer tieferen Franchise (bis 30.11., KVV Art. 94 Abs. 2) ist nicht
  als eigene Frist umgesetzt.
- Der Checkpointer liegt im Arbeitsspeicher; nach einem Neustart sind offene Rückfragen weg.
- Haiku läuft mit Standard-Temperatur, die Ergebnisse streuen um ±1 Brief.

## 8. Nächste Schritte

- **Plausibilitätsprüfung der Analyse:** z. B. Zustelldatum nicht vor dem Briefdatum (hätte 62
  verhindert), Summe der Posten gegen den Hauptbetrag auch bei Steuerbriefen (13, 63).
- **Eigener Prüfschritt für Prompt Injection**, getrennt von der Analyse.
- **Echte, geschwärzte Briefe** als zweiter Hold-out.
- **Kanton aus der Adresse** bestimmen und kantonale Feiertage ergänzen.
- **Persistenter Checkpointer** (SQLite oder Postgres) für einen echten Betrieb.
- **Apertus mit eigenen Prompts:** offenes Schweizer Modell, für echte Briefe mit Personendaten
  datenschutzfreundlicher.

## 9. Einsatz von KI-Werkzeugen

Beim Programmieren, bei Datengenerator und Dokumentation haben wir Claude (Anthropic) als
Assistenten eingesetzt. Commits von `Claude` bzw. mit «Co-Authored-By: Claude» sind so entstanden.
Anwendungsfall, Umfang, Architektur- und Modellentscheide sowie die Auswertung der Ergebnisse lagen
beim Team; alle Änderungen liefen über Pull Requests, die das Team geprüft und gemergt hat.
