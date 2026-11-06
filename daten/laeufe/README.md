# Läufe des Agenten

Ausgaben von `python main.py _ --variante <pdf|scan|foto>` über alle 45 Testbriefe,
geprüft gegen `gold.json` (Brieftyp, Fristen, Betrag, Injection; bei unlesbaren Fotos
nur die Erkennung als unlesbar). Modell: `azure_ai/claude-haiku-5-5` über LiteLLM.

Dateiname: `<Datum>_<Uhrzeit>_<Variante>.txt`. Neue Läufe hier ablegen (`ausgabe/` ist
nicht im Git).

| Datei | Variante | Ergebnis | Bemerkung |
|---|---|---|---|
| 2026-11-04_1129_foto_v2.txt | foto | 37/45 | vor dem Graph-Gerüst (Analyse → Fristen → Erklärung) |
| 2026-11-04_1139_ocr_auswertung.txt | pdf/scan/foto | – | nur OCR-Textqualität, Log von `ocr_auswertung.py` (Tabelle: `daten/ocr_auswertung.md`) |
| 2026-11-06_0934_foto.txt | foto | 36/45 | 9-Node-Graph mit Guardrail |
| 2026-11-06_0946_scan.txt | scan | 37/45 | 9-Node-Graph mit Guardrail; 03 und 04 mit `Connection error` zum Proxy abgebrochen |
| 2026-11-06_1001_foto.txt | foto | 29/45 | 9-Node-Graph mit Guardrail |
