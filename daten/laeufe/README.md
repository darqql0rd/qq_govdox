# Läufe des Agenten

Ausgaben von `python main.py _ --variante <pdf|scan|foto>` über alle 45 Testbriefe,
geprüft gegen `gold.json` (Brieftyp, Fristen, Betrag, Injection; bei unlesbaren Fotos
nur die Erkennung als unlesbar). Modell: `azure_ai/claude-haiku-5-5` über LiteLLM.

Dateiname: `<Datum>_<Uhrzeit>_<Variante>.txt` (Zeitpunkt des Laufs). Neue Läufe hier ablegen (`ausgabe/` ist
nicht im Git).

| Datei | Variante | Ergebnis | Bemerkung |
|---|---|---|---|
| 2026-11-04_1054_foto_v1.txt | foto | 29/45 | erster Foto-Lauf, vor dem Graph-Gerüst |
| 2026-11-04_1129_foto_v2.txt | foto | 37/45 | vor dem Graph-Gerüst (Analyse → Fristen → Erklärung) |
| 2026-11-04_1139_ocr_auswertung.txt | pdf/scan/foto | – | nur OCR-Textqualität, Log von `ocr_auswertung.py` (Tabelle: `daten/ocr_auswertung.md`) |
| 2026-11-06_0934_foto.txt | foto | 36/45 | 9-Node-Graph mit Guardrail |
| 2026-11-06_0946_scan.txt | scan | 37/45 | 9-Node-Graph mit Guardrail; 03 und 04 mit `Connection error` zum Proxy abgebrochen |
| 2026-11-09_foto_1.txt | foto | 38/45 | nach #8–#13 (Fristen-Rechtsprüfung, Retry, Guardrail-/Prompt-Regeln); 5 Briefe am Guardrail-Limit |
| 2026-11-09_foto_2.txt | foto | 36/45 | wie foto_1; 4 Briefe am Guardrail-Limit |
| 2026-11-09_foto_3.txt | foto | 34/45 | wie foto_1; 5 Briefe am Guardrail-Limit, 2 Abstürze (ValidationError) |
| 2026-11-09_scan_1.txt | scan | 39/45 | wie foto_1; 2 Briefe am Guardrail-Limit |
| 2026-11-09_auswertung.md | – | – | Auswertung der vier Läufe vom 09.11. im Vergleich zum 06.11. |

## Befunde

- **Brief 44 (commination de faillite, FR), Betrag falsch** in den Läufen vom 06.11.
  (foto 9'943.30, scan 9'993.30, erwartet 10'003.30): Die OCR liest alle Beträge richtig
  (CHF 9 870,00 + 83,30 + 50,00), aber der Brief nennt kein Total, und das LLM zählt die
  Posten falsch zusammen. Die Summenprüfung `posten_plausibel()` in `nodes/analyse.py`
  läuft nur bei Zahlungsbefehl und Mahnung, deshalb fällt der Fehler nicht auf.
