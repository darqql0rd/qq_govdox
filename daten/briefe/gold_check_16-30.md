# Gold-Check 16–30 (Nayan)

Geprüft am 26.10.2026 gegen `brief.pdf` / `text.txt`, Fristen selbst nachgerechnet nach `fristen_herleitung.md` und `datengenerator/fristen.py`.
Ergebnis: keine Fehler, nichts korrigiert. `python datengenerator/pruefe_gold.py` → OK.

| Brief | OK / Fehler | Feld | steht im Gold | steht im Brief | korrigiert |
|---|---|---|---|---|---|
| 16 | OK | – | – | – | nein |
| 17 | OK | – | – | – | nein |
| 18 | OK | – | – | – | nein |
| 19 | OK | – | – | – | nein |
| 20 | OK | – | – | – | nein |
| 21 | OK | – | – | – | nein |
| 22 | OK | – | – | – | nein |
| 23 | OK | – | – | – | nein |
| 24 | OK | – | – | – | nein |
| 25 | OK | – | – | – | nein |
| 26 | OK | – | – | – | nein |
| 27 | OK | – | – | – | nein |
| 28 | OK | – | – | – | nein |
| 29 | OK | – | – | – | nein |
| 30 | OK | – | – | – | nein |

## Zur gemeinsamen Entscheidung

1. **Krankenkasse 20–25, Summenregel:** `hauptbetrag_chf` ist das Monatstotal 2027, die `posten` enthalten aber 2026 und 2027. Die Summe der Posten entspricht also nicht dem Hauptbetrag. `pruefe_gold.py` nimmt `krankenkasse_praemie` bewusst aus; Punkt 4 der Prüfanleitung gilt hier nicht.
2. **Rappen-Rundung im Brief (16, 19):** 65 % von 3'535.90 = 2'298.335, gedruckt 2'298.35 (16); 155 % von 2'477.80 = 3'840.59, gedruckt 3'840.60 (19). Gold übernimmt korrekt die gedruckten Werte; kleiner Schönheitsfehler im Generator.
3. **Fristregeln:** Die Annahme Zustellung = Briefdatum + 2 Werktage und die Regeln selbst sind noch nicht gegen Fedlex geprüft.
