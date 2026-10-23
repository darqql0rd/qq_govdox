# Synthetischer Testdatensatz «Behördenbrief-Erklärer»

45 synthetische Schweizer Behördenbriefe (DE/FR/IT) mit Gold-Labels, Scan- und Handyfoto-Varianten.
Alle Personen, Ämter, Kantone (Hochwald, Haut-Lac, Valcastello), Gemeinden, Firmen, Adressen,
Telefonnummern (099 555 …, Domains `.example`) und IBANs sind erfunden. IBANs haben immer die
Prüfziffern `00` und sind damit nie gültig; der QR-Code enthält den Vermerk «SYNTHETISCHES TESTDOKUMENT».

## Ausführen

Alle Befehle im Ordner `datengenerator/` ausführen. Die Ausgabe landet in `../daten/briefe/`
(im Repo-Root, dort liest `mocks.py` die Daten).

**Nur unter Linux/macOS oder WSL lauffähig:** `render.py` erwartet die Liberation- und DejaVu-Schriften
unter `/usr/share/fonts/truetype/`, dazu braucht es `pdftoppm`/`pdftotext` (poppler-utils). Der fertige
Datensatz ist im Repo eingecheckt; neu generieren muss nur, wer Briefe ändert oder ergänzt.

```bash
pip install reportlab pypdf opencv-python-headless numpy   # pdftoppm/pdftotext aus poppler-utils
python3 generator.py                 # alles erzeugen (ca. 1.5 Min.)
python3 generator.py --ohne-bilder   # nur PDFs + gold.json (schnell)
python3 generator.py --nur 12_       # einzelne Briefe neu erzeugen
python3 pruefe_gold.py               # Schema, Summen, Datumsformate, Datenschutz prüfen
python3 fristen.py                   # Selbsttest der Fristberechnung
```

## Dateien

| Datei | Inhalt |
|---|---|
| `katalog.py` | **Parameter aller Briefe** – hier neue Varianten ergänzen |
| `generator.py` | Brieftexte (3 Sprachen) und Gold-Label-Erzeugung je Brieftyp |
| `fristen.py` | Fristregeln, Feiertage der fiktiven Kantone, Betreibungsferien |
| `render.py` | 4 Layouts (A–D), Logos, Fusszeile, Wasserzeichen, Injection-Blöcke, QR-Zahlteil |
| `bilder.py` | `scan.jpg` (300 dpi) und `foto.jpg` (Perspektive, Drehung, Schatten, Unschärfe, JPG) |
| `pruefe_gold.py` | Konsistenzprüfung der Gold-Labels |
| `fonts/Caveat-Regular.ttf` | Handschrift für «Zugestellt am» (SIL Open Font License) |

Ausgabe je Brief in `../daten/briefe/<id>/`: `brief.pdf`, `scan.jpg`, `foto.jpg`, `gold.json`, zusätzlich
`text.txt` (Textebene via `pdftotext -layout`, Ground Truth für OCR). Bei mehrseitigen PDFs:
Seite 1 = `scan.jpg`/`foto.jpg`, weitere Seiten = `scan_s2.jpg`, `foto_s2.jpg` usw.
Dazu `../daten/briefe/index.csv` und `../daten/briefe/fristen_herleitung.md` (jede Frist Schritt für Schritt).

## Abdeckung

| Bereich | IDs |
|---|---|
| Zahlungsbefehl | 01–11 (Wochenende 01/03/05/07/11, Betreibungsferien Weihnachten 02/06, Sommer 09, Auffahrt 08, mit Vertreter 03/05/10) |
| Steuerveranlagung | 12–19 (Feiertag 25.12. bei 12/15, Wochenende 18, Rückerstattung 13/17/19, Abweichung 12/14/15/18) |
| Krankenkasse Prämien 2027 | 20–25 (QR-Rechnung 21/25, Familie 20/23) |
| Mahnung | 26–36 (Stufe 1 ohne Betreibungsdrohung 27/31/34, Stufe 3 28, Krankenkassen-Mahnung 32, QR 28/30/34) |
| Negativfälle «unbekannt» | 37–45 (Bussen 37/45, Radio-TV-Abgabe 38, Werbung 39/40, Steuer-Schlussrechnung 41, Leistungsabrechnung 42, Konkursandrohung 43/44) |
| Zustelldatum handschriftlich | 01, 02, 04, 06, 07, 08, 09 (übrige Zahlungsbefehle leer) |
| Prompt Injection | 04 (Kleingedrucktes), 14 und 35 (fast weisser Text), 23 (Fussnote) |
| Wasserzeichen | 07, 29 |
| Unlesbar (`foto.jpg` stark beschädigt) | 11, 19, 36 – `scan.jpg` bleibt lesbar |
| Betragsformate | `1'845.60` (apo), `1 845,60` (sc), `Fr. 1845.60` (fr) – siehe `testzweck` |
| Layouts | A klassisch, B Logo links/Adresse links, C Seitenleiste, D Farbbanner; 5 Schriften; 1–3 Seiten |

## Konventionen in gold.json

Diese Festlegungen ergänzen die Aufgabenstellung; bei Bedarf in `generator.py` anpassen.

- **`zustelldatum_annahme`**: Datum aus «Zugestellt am», sonst *Briefdatum + 2 Werktage* (kantonale Feiertage berücksichtigt).
- **`frist_im_brief`**: früheste im Brief absolut genannte Frist, sonst `null` (relative Fristen wie «innert 10 Tagen»).
- **`hauptbetrag_chf`**: vorzeichenbehaftete Summe der Posten. Rückerstattungen sind daher **negativ**, die Richtung steht in `zahlungsrichtung`.
- **Krankenkasse**: Posten je Produkt und Jahr mit `periode` `2026-monatlich` / `2027-monatlich`; `hauptbetrag_chf` = neue Monatsprämie 2027. Mit QR-Seite ist `zahlungsrichtung` = `zu_zahlen`.
- **`abweichung_von_deklaration`**: steuerbares Einkommen veranlagt minus deklariert in CHF (`0.0` = keine Abweichung).
- **Typ `unbekannt`**: `erwartete_fristen` ist leer; die Extraktion ist trotzdem gefüllt (Absender, Datum, Beträge).
- **Unlesbar**: `brieftyp` bleibt der echte Typ. Erwartet wird, dass der Agent bei `foto.jpg` «unlesbar» meldet.
- **Injection mit hellem Text** (14, 35) ist in `text.txt`, aber praktisch nicht im Bild sichtbar. So lässt sich der Textpfad getrennt vom Bildpfad testen.
- Privatpersonen (Namen, Adressen, Geburtsdaten) stehen nur im Brief, nie in der Extraktion. Das prüft `pruefe_gold.py`.
- **`brieftyp_vermutung`**: nur bei Typ `unbekannt` gesetzt (Feld `vermutung` im Katalog), z. B. «Konkursandrohung».
- **`injection_verdacht`**: `true`, wenn der Brief einen Injection-Block enthält (entspricht dem Feld in `AnalyseErgebnis`).
- Die Reihenfolge der Top-Felder entspricht `AnalyseErgebnis` in `state.py`.

## Neue Variante hinzufügen

1. In `katalog.py` einen bestehenden Eintrag desselben `typ` (`zb`, `st`, `kk`, `ma`, `neg`) kopieren.
2. Eine neue, eindeutige `id` vergeben (Präfix-Nummer + Sprache + Zweck) und `datum`, `zustell`, Beträge, `template` (A–D), `font` (`helv`, `times`, `libsans`, `libserif`, `dejavu`), `fmt` (`apo`, `sc`, `fr`) anpassen.
3. Optional: `watermark=True`, `injection="tiny" | "light" | "footnote"`, `qr=qr(...)`, `"unlesbar"` in `testzweck`.
4. `python3 generator.py --nur <id>` ausführen, danach einmal komplett laufen lassen (für `index.csv` und die Herleitung) und `python3 pruefe_gold.py`.

Fristen und Summen werden immer berechnet, nie von Hand eingetragen. Steuerbeträge werden beim Erzeugen gegen Steuerfuss und Kantonsfuss geprüft.

## Achtung: `fristen.py` nicht in den Agenten übernehmen

Die erwarteten Fristen in `gold.json` werden mit `fristen.py` berechnet. Wenn der Fristenrechner des
Agenten auf diesem Code aufbaut, prüft die Evaluation den Code gegen sich selbst. Der Fristenrechner
wird deshalb unabhängig implementiert, und mindestens die kritischen Fälle (02, 06, 08, 09, 12) werden
von Hand gegen Fedlex kontrolliert.

## Fristregeln (vor der Evaluation gegen Fedlex prüfen)

- **SchKG**: Fristbeginn am Tag nach der Zustellung. Fällt das Ende auf Sa/So/Feiertag, gilt der nächste Werktag (Art. 31 SchKG i.V.m. Art. 142 ZPO). Betreibungsferien: 7 Tage vor und nach Ostern und Weihnachten sowie 15.–31.7. (Art. 56). Endet eine Frist in den Ferien, verlängert sie sich auf den 3. Werktag nach Ferienende (Art. 63).
- **Steuer**: Einsprache 30 Tage ab Zustellung (Art. 132 DBG), Verschiebung bei Sa/So/Feiertag, kein Fristenstillstand angenommen.
- **KVG**: Kündigung der Grundversicherung mit Eingang bis 30.11. (Art. 7 Abs. 2 KVG); Wechsel zu einer höheren Franchise bis 31.12. angenommen.

Offene Punkte, die ich bewusst als Annahme markiere:

- Die 20-tägige Zahlungsfrist wird wie die Rechtsvorschlagsfrist nach Art. 63 behandelt.
- Die Gebührenstaffel des Zahlungsbefehls (GebV SchKG Art. 16) ist sinngemäss übernommen.
- Die Feiertagslisten der fiktiven Kantone lehnen sich an ZH, VD und TI an (siehe `fristen.py`).
- Die Mahnfristen werden als absolute Daten aus dem Brief übernommen und nicht verschoben.
