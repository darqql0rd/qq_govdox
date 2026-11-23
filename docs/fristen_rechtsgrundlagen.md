# Fristen: Rechtsgrundlagen und Prüfung

Was der Fristenrechner ([`fristenrechner.py`](../fristenrechner.py), Vendon) umsetzt, auf welcher
Grundlage, und was bewusst fehlt. Der Rechner arbeitet ohne LLM; der Fristen-Node ruft ihn
deterministisch auf.

## Umgesetzte Regeln

| Regel | Grundlage | Im Code |
|---|---|---|
| Rechtsvorschlag 10 Tage ab Zustellung | SchKG Art. 74 | `REGELN["zahlungsbefehl"]` |
| Zahlung 20 Tage ab Zustellung | SchKG Art. 69 | `REGELN["zahlungsbefehl"]` |
| Einsprache 30 Tage ab dem Tag nach Zustellung | DBG Art. 132 Abs. 1 | `REGELN["steuerveranlagung"]` |
| Frist beginnt am Tag nach der Zustellung | SchKG Art. 31 i.V.m. ZPO Art. 142 Abs. 1 | `fristen_berechnen` |
| Fristende auf Samstag, Sonntag oder Feiertag → nächster Werktag | ZPO Art. 142 Abs. 3 | `_fristende` |
| Zahlungsbefehl am Samstag zugestellt: Frist läuft trotzdem ab Sonntag | ZPO Art. 142 Abs. 1bis gilt nicht für Betreibungsurkunden (OG SH, 16.12.2025) | keine Verschiebung des Beginns |
| Betreibungsferien: 7 Tage vor und nach Ostern und Weihnachten, 15.–31. Juli | SchKG Art. 56 Ziff. 2 | `betreibungsferien` |
| Fristende in den Betreibungsferien → bis zum 3. Werktag nach Ferienende | SchKG Art. 63 | `_fristende` |
| Zustellung während der Betreibungsferien wirkt erst am Tag nach den Ferien | BGE 121 III 284 E. 2b, BGE 127 III 173 E. 3b | `wirksame_zustellung` |
| Rechtsvorschlag und Einsprache: Postaufgabe am letzten Tag genügt | SchKG Art. 32 Abs. 1 | Guardrail-Regel gegen «muss beim Amt ankommen» |
| Krankenkasse: Kündigung bis 30.11., Eingang beim Versicherer massgebend | KVG Art. 7 Abs. 2 | Frist aus dem Brief, Hinweis `eingang_massgebend` |
| Mahnung: keine gesetzliche Frist | – | Frist aus dem Brief, nicht verschoben |

Betreibungsferien gelten nur für den Zahlungsbefehl, nicht für die Steuer.

## Feiertage

Bundesrechtlich ist nur der 1. August ein Feiertag (BV Art. 110 Abs. 3); alle anderen legen die
Kantone fest. Der Agent kennt den Kanton nicht. Darum zählt der Rechner nur Feiertage, die in
(fast) allen Kantonen gelten: Neujahr, Ostermontag, Auffahrt, Pfingstmontag, 1. August und
Weihnachten.

Bewusst nicht gezählt: Berchtoldstag, Karfreitag (kein Feiertag in TI und VS), Stephanstag (kein
Feiertag in VS) und alle rein kantonalen Feiertage. Fällt ein Fristende auf einen dieser Tage,
nennt der Rechner diesen Tag statt des nächsten Werktags. **Die Frist ist dann höchstens zu früh,
nie zu spät.** Wer zu früh handelt, verliert nichts.

Ausnahme: Ostermontag und Pfingstmontag gelten im Wallis nicht eindeutig (die Quellen
widersprechen sich). Sie sind trotzdem enthalten, weil sie in fast der ganzen Schweiz gelten. Dort
könnte eine Frist in seltenen Fällen einen Tag zu spät sein. Offen: gegen die Liste der
kantonalen Feiertage des Bundesamts für Justiz prüfen.

## Zustelldatum

Die Fristen beginnen mit der Zustellung, nicht mit dem Briefdatum.

- Steht das Zustelldatum im Brief (beim Zahlungsbefehl «Zugestellt am» auf Seite 2), wird es
  übernommen.
- Sonst fragt der Graph die Person (`interrupt()`). Weiss sie es nicht, gilt das Briefdatum als
  Schätzung; die Frist wird damit eher zu früh, und die Ausgabe weist darauf hin.
- Ein Zustelldatum vor dem Briefdatum ist unmöglich und wird wie «weiss nicht» behandelt.

## Rechtsprüfung vom 09.11.2026

Der Rechner wurde gegen Gesetzestext, Bundesgerichtspraxis und das Merkblatt des BAG geprüft. Den
Wortlaut haben wir aus Abschriften (law.ch) und Gerichtsentscheiden übernommen, weil Fedlex nur
per JavaScript lädt.

| Befund | Status |
|---|---|
| Zustellung während der Betreibungsferien wurde ab der tatsächlichen Zustellung gerechnet, die Frist war zu früh. Beispiel: Zustellung 22.12.2026 → Rechtsvorschlag bis 12.01.2027 statt 06.01.2027 | behoben (PR #8) |
| Karfreitag und Stephanstag wurden für alle Briefe gezählt; im Tessin konnte eine Frist dadurch zu spät sein. Beispiel: Tassazione TI, Zustellung 04.03.2026 → Fristende 03.04.2026, nicht 07.04.2026 | behoben (PR #8) |
| Krankenkasse: Wechsel zu einer höheren Franchise wirkt ab 1.1. (KVV Art. 94 Abs. 1); der Rechner nennt den 31.12. als letzten möglichen Tag, das ist aber keine gesetzliche Frist. Wechsel zu einer tieferen Franchise oder einem anderen Modell (bis 30.11. eintreffend, KVV Art. 94 Abs. 2) fehlt als eigene Frist | offen |

Tests: [`tests/teste_fristenrechner.py`](../tests/teste_fristenrechner.py) prüft alle Testbriefe
mit gesetzlicher Frist gegen das Gold-Label und zusätzlich die Rechtsfälle oben.

## Prüfung gegen den Datengenerator

Die erwarteten Fristen im Gold-Label stammen aus einer eigenen Fristenlogik des Generators
(`datengenerator/fristen.py`), die unabhängig vom Fristenrechner geschrieben wurde. Die beiden
rechnen in zwei Punkten absichtlich verschieden: Der Generator kennt kantonale Feiertage, und er
setzt die Regel zur Zustellung während der Betreibungsferien nicht um. Für den Hold-out wurden
deshalb nur Briefe ohne diese Fälle erzeugt; für alle 20 liefert der Fristenrechner genau die
erwarteten Fristen.

In der Evaluation kam kein Fristfehler aus der Berechnung selbst. Falsche Fristen entstanden nur
aus falschen Eingaben: einem falsch gelesenen handschriftlichen Zustelldatum (Briefe 04, 49) oder
einem falsch erkannten Brieftyp (Hold-out 62).

## Ausblick

Ein neues Bundesgesetz soll Mitteilungen ohne Unterschrift (z. B. A-Post Plus), die an einem
Samstag, Sonntag oder Feiertag ankommen, erst am nächsten Werktag als zugestellt gelten lassen. Laut
Vernehmlassung (Juni 2026) ist die Inkraftsetzung per 1.1.2028 vorgesehen; es betrifft dann vor
allem die Steuerveranlagung. Zahlungsbefehle werden gegen Unterschrift zugestellt und sind nicht
betroffen.
