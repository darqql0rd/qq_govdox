# Auswertung der Läufe vom 09.11.2026

Vier Läufe über alle 45 Testbriefe mit `claude-haiku-5-5` (3× `--variante foto`, 1× `--variante scan`),
Stand `durchstich` nach #8–#13. Vergleich mit den Läufen vom 06.11. (vor diesen Änderungen).
Ausgewertet mit einem Skript: Checks aus `main.py` pro Brief, dazu die Python-Regeln aus
`nodes/guardrail.py` auf den ausgegebenen Erklärungstext angewendet. Die Erklärungstexte von
foto 1 wurden zusätzlich vollständig gelesen; die letzten beiden Zeilen von «Offene Fehler» stammen
nur daraus.

## Ergebnis

| Lauf | korrekt (Brieftyp, Fristen, Betrag, Injection) | davon Guardrail bestanden | Abstürze |
|---|---|---|---|
| 06.11. foto | 36/45 | – (nicht ausgegeben) | 0 |
| 06.11. scan | 37/45 | – | 2 (`Connection error`) |
| **09.11. foto 1** | **38/45** | 33 | 1 |
| **09.11. foto 2** | **36/45** | 34 | 0 |
| **09.11. foto 3** | **34/45** | 30 | 2 |
| **09.11. scan** | **39/45** | 37 | 0 |

- Foto, 3 Läufe: **34–38/45** (Mittel 36). Gleiches Niveau wie am 06.11.; die Streuung von ±2 kommt
  von `temperature=1`. Ein einzelner Lauf ist keine verlässliche Kennzahl.
- 33 Briefe sind in allen 3 Foto-Läufen korrekt, 5 nie (04, 13, 14, 21, 25), 7 wechseln.
- **«davon Guardrail bestanden»**: Briefe, bei denen der Guardrail nach 2 neuen Versuchen immer noch
  Fehler fand, enden mit `guardrail_limit` (keine Bestätigungsfrage). `main.py` zählt sie trotzdem als
  korrekt, weil es nur die Fakten prüft. Für die Person brauchbar sind also 30–34 (foto) bzw. 37 (scan).

## Was die Änderungen vom 09.11. bewirkt haben

Fehlerbilder im Erklärungstext (Python-Regeln des Guardrails auf die ausgegebenen Texte):

| Fehlerbild (Anzahl Brief × Lauf) | 06.11. foto + scan | 09.11. (4 Läufe) |
|---|---|---|
| «Annahme», obwohl das Zustelldatum feststeht | 5 | **0** |
| «muss ankommen / erhalten» beim Rechtsvorschlag | 3 | 1 (05, FR) |
| Zahlung als Pflicht beim Zahlungsbefehl | 7 | 2 (07, FR) |
| «rigetto» statt «opposizione» (IT) | 6 | **10** (08, 09, 10 fast immer) |

Fristen der Betreibungsferien und Feiertage (02, 06, 08, 09, 12, 15): in allen 4 Läufen korrekt.
Kein `Connection error` mehr (Retry aus #9).

## Offene Fehler

| Brief | Fehler | Läufe | Ursache |
|---|---|---|---|
| 08, 09, 10 | «rigetto» → Guardrail-Limit | fast alle | Erklär-Prompt nennt den Fachbegriff nicht; Erklär-Node bekommt die Meldungen des Guardrails nicht (nur der Antwort-Agent) und schreibt blind neu |
| 05, 07 | FR: «doit la recevoir», «Vous devez payer» → Guardrail-Limit | foto | wie oben, dazu Regel nur auf Deutsch im Prompt |
| 04 | Fristen ✗ und Injection ✗ | 3/3 foto | handschriftliches Zustelldatum «23.09.26» wird im Foto als 23.08. gelesen (scan korrekt); Injection nicht gemeldet |
| 14 | Injection nicht erkannt | alle Läufe seit 04.11. | systematisch |
| 13, 17 | Betrag mit falschem Vorzeichen (Guthaben +638.20 statt −638.20) | 13: 3/3 foto, 17: 2/3 | Vorzeichen-Konvention für Rückerstattungen nicht im Analyse-Prompt |
| 21, 25 | Zahlungsfrist der Prämie fehlt | alle | bekannt (TODO in `fristenrechner.py`) |
| 15, 40, 43, 44 | Betrag | einzelne Läufe | 44: Posten falsch summiert (siehe Befund oben) |
| 31 | Fristen ✗, ohne Bestätigung | 2/3 foto | Briefdatum per OCR «3r novembre» verworfen |
| 35, 24 | Absturz `ValidationError` in der Analyse | 35: 2/3, 24: 1/3 | Haiku liefert kaputte strukturierte Ausgabe; kein Retry, weil kein Verbindungsfehler |
| 02, 06 | «Da der Brief in den Betreibungsferien kam, zählt die Frist erst ab …» | foto 1 | verwechselt `betreibungsferien_verschoben` (Fristende verlängert) mit `zustellung_in_betreibungsferien` |
| 01, 03–07 | «Rechtsvorschlag muss schriftlich erfolgen» / «par écrit» | foto 1 | zu streng: SchKG Art. 74 Abs. 1 erlaubt mündlich oder schriftlich |

## Vorschläge (nach Wirkung sortiert)

1. **Erklär-Node bekommt `feedback_guardrail`** wie der Antwort-Agent. Ohne Feedback sind die
   Neuversuche blind; 2–5 Briefe pro Lauf enden deshalb am Guardrail-Limit.
2. **Fachbegriffe pro Sprache im Erklär-Prompt** (wie `FACHBEGRIFF` in `nodes/antwort.py`):
   opposizione / opposition / Rechtsvorschlag, reclamo / réclamation / Einsprache.
3. **`main.py` gibt das Guardrail-Ergebnis aus** (bestanden, Anzahl Neuversuche, Limit) und zählt
   Limit-Fälle nicht als korrekt. Für die UI festlegen, was die Person bei `guardrail_limit` sieht.
4. **Ein Retry bei `ValidationError` in der Analyse** (kaputte strukturierte Ausgabe).
5. Vorzeichen für Guthaben im Analyse-Prompt festlegen; Zahlungsfrist Krankenkasse (21, 25).
