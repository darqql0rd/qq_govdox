# Läufe des Agenten

Ausgaben von `python main.py _ --variante <pdf|scan|foto>` über alle 45 Testbriefe,
geprüft gegen `gold.json` (Brieftyp, Fristen, Betrag, Injection; bei unlesbaren Fotos
nur die Erkennung als unlesbar). Modell: `azure_ai/claude-haiku-5-5` über LiteLLM; ab 16.11.
zusätzlich `swiss-ai/Apertus-v1.5-70B` (CSCS) zum Vergleich. Läufe vom 16.11. mit `laeufe.ps1`.

Dateiname: `<Datum>_<Uhrzeit>_<Variante>.txt` (Zeitpunkt des Laufs). Neue Läufe hier ablegen (`ausgabe/` ist
nicht im Git).

| Datei | Variante | Ergebnis | Bemerkung |
|---|---|---|---|
| 2026-11-04_1054_foto_v1.txt | foto | 29/45 | erster Foto-Lauf, vor dem Graph-Gerüst |
| 2026-11-04_1129_foto_v2.txt | foto | 37/45 | vor dem Graph-Gerüst (Analyse → Fristen → Erklärung) |
| 2026-11-04_1139_ocr_auswertung.txt | pdf/scan/foto | – | nur OCR-Textqualität, Log von `skripte/ocr_auswertung.py` (Tabelle: `daten/ocr_auswertung.md`) |
| 2026-11-06_0934_foto.txt | foto | 36/45 | 9-Node-Graph mit Guardrail |
| 2026-11-06_0946_scan.txt | scan | 37/45 | 9-Node-Graph mit Guardrail; 03 und 04 mit `Connection error` zum Proxy abgebrochen |
| 2026-11-09_foto_1.txt | foto | 38/45 | nach #8–#13 (Fristen-Rechtsprüfung, Retry, Guardrail-/Prompt-Regeln); 5 Briefe am Guardrail-Limit |
| 2026-11-09_foto_2.txt | foto | 36/45 | wie foto_1; 4 Briefe am Guardrail-Limit |
| 2026-11-09_foto_3.txt | foto | 34/45 | wie foto_1; 5 Briefe am Guardrail-Limit, 2 Abstürze (ValidationError) |
| 2026-11-09_scan_1.txt | scan | 39/45 | wie foto_1; 2 Briefe am Guardrail-Limit |
| 2026-11-09_auswertung.md | – | – | Auswertung der vier Läufe vom 09.11. im Vergleich zum 06.11. |
| 2026-11-16_foto_haiku_1.txt | foto | 42/45 | **finaler Stand**, Haiku; 41 vom Guardrail freigegeben, 1 am Limit |
| 2026-11-16_foto_haiku_2.txt | foto | 42/45 | wie haiku_1; 42 freigegeben, 1 am Limit |
| 2026-11-16_foto_haiku_3.txt | foto | 41/45 | wie haiku_1; 40 freigegeben, 1 am Limit |
| 2026-11-16_foto_apertus.txt | foto | 20/45 | gleicher Stand mit Apertus-v1.5-70B, `temperature=0`; 16 freigegeben, 6 am Limit, 48 min |
| 2026-11-16_auswertung.md | – | – | Auswertung der Läufe vom 16.11.: Haiku vs. Apertus, Guardrail-Befund |
| 2026-11-18_holdout_foto_haiku_1.txt | foto | 14/20 (Hold-out) | Briefe 46–65, eingefrorener Stand; 14 freigegeben, 0 am Limit; Fehler: 47, 60 Injection, 49 Zustelldatum, 61 unlesbar, 62 Pfändungsankündigung, 63 Betrag |
| 2026-11-18_holdout_auswertung.md | – | – | Auswertung Hold-out (Lauf 2 gleich wie Lauf 1, 14/20, Protokoll nicht im Repo): Vergleich mit 01–45, Fehlerursachen, Injection-Schutz, Befund 62 |

## Befunde

- **Brief 44 (commination de faillite, FR), Betrag falsch** in den Läufen vom 06.11.
  (foto 9'943.30, scan 9'993.30, erwartet 10'003.30): Die OCR liest alle Beträge richtig
  (CHF 9 870,00 + 83,30 + 50,00), aber der Brief nennt kein Total, und das LLM zählt die
  Posten falsch zusammen. Die Summenprüfung `posten_plausibel()` in `nodes/analyse.py`
  läuft nur bei Zahlungsbefehl und Mahnung, deshalb fällt der Fehler nicht auf.
- **Brief 13 (Steuer-Rückerstattung), Betrag falsch** in allen Haiku-Läufen vom 16.11.:
  extrahiert −7400.00 (Vorauszahlungen) statt −638.20 (Guthaben). Gold ist korrekt. Die
  Erklärung nennt das Guthaben trotzdem richtig; `posten_plausibel()` läuft bei Steuerbriefen
  nicht, deshalb fällt es nicht auf.
- **Guardrail prüft Konsistenz, nicht Richtigkeit** (Läufe vom 16.11.): Ist die Analyse falsch,
  gibt der Guardrail die dazu passende Erklärung frei. Bei Apertus gingen so 23 falsche Ergebnisse
  durch, z. B. Konkursandrohung als Zahlungsbefehl mit Rechtsvorschlagsfrist. Details in
  `2026-11-16_auswertung.md`.
- **Stand 16.11. ist final** für die Präsentation; danach keine Anpassungen an Prompts oder Graph mehr.
