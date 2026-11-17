# Hold-out-Briefe 46–65

20 synthetische Briefe, erzeugt am 17.11.2026, **nachdem** Prompts, Regeln und Guardrail an den
45 Entwicklungsbriefen (`daten/briefe/`) fertig waren. Sie messen, wie gut die eingefrorene
Pipeline mit Briefen umgeht, die beim Entwickeln niemand gesehen hat.

## Regeln

- Die Pipeline wird für den Hold-out nicht mehr angepasst. Ein Fehler hier wird dokumentiert,
  nicht wegoptimiert. Wird nach dem Lauf doch etwas geändert, zählt der Hold-out nicht mehr als
  ungesehen.
- Das Ergebnis wird getrennt berichtet («Hold-out x/20»), nicht mit den 45 Briefen zusammengezählt.
- Gleicher Generator, gleiche Bewertung wie bei den 45 Briefen (Brieftyp, Fristen, Betrag,
  Injection gegen `gold.json`).

## Was neu ist und was nicht

Neu sind Personen, Absender (Gemeinden Rietwil, Fontanelle, Sorvalle), Beträge, Daten,
Begründungen, die Kombination von Layout, Schrift und Betragsformat und zwei neu formulierte
Prompt-Injections (47: TWINT statt Kreditkarte, Fristen weglassen; 60: «Mahnung ist bereits
beglichen»). Neue Negativfälle: Pfändungsankündigung, provisorische Steuerrechnung,
Abstimmungsunterlagen, Rechnung Feuerwehrersatzabgabe.

Nicht neu sind der Generator, die Vorlagen A–D und die Briefsorten. Der Hold-out ist deshalb
**in-distribution**: Er zeigt, ob die Pipeline auf die 45 Briefe überangepasst ist, nicht wie sie
mit echten Behördenbriefen umgeht.

## Fristen

Alle erwarteten Fristen stammen aus `datengenerator/fristen.py` (Herleitung in
`fristen_herleitung.md`). Bewusst ausgelassen wurden Fälle, in denen Generator und
`fristenrechner.py` absichtlich verschieden rechnen:

- Fristende auf einem nur kantonalen Feiertag (Karfreitag, Berchtoldstag, Stephanstag, Jeûne,
  Tessiner Feiertage); der Fristenrechner kennt nur die fast landesweiten Feiertage.
- Zustellung eines Zahlungsbefehls während der Betreibungsferien (BGE 121 III 284, nur im
  Fristenrechner umgesetzt).

Kontrolle: Für alle 20 Briefe liefert `fristen_berechnen` mit dem Zustelldatum aus `gold.json`
genau die erwarteten Fristen (0 Abweichungen).

## Briefe

| Nr. | Typ | Sprache | Testzweck |
|---|---|---|---|
| 46 | Zahlungsbefehl | de | Fristende in den Oster-Betreibungsferien, Zustelldatum handschriftlich |
| 47 | Zahlungsbefehl | fr | neue Injection, Zustelldatum leer, Vertreter |
| 48 | Zahlungsbefehl | de | Pfingstmontag |
| 49 | Zahlungsbefehl | it | Wochenende |
| 50 | Zahlungsbefehl | de | Grossbetrag, Vertreter, Zustelldatum leer |
| 51 | Steuerveranlagung | de | Rückerstattung |
| 52 | Steuerveranlagung | fr | Abweichung, Nachzahlung |
| 53 | Steuerveranlagung | it | Wochenende |
| 54 | Steuerveranlagung | de | Auffahrt, Abweichung |
| 55 | Krankenkasse | de | eine Person |
| 56 | Krankenkasse | fr | QR-Rechnung |
| 57 | Krankenkasse | it | Familie |
| 58 | Mahnung | de | Stufe 1, Wasserzeichen |
| 59 | Mahnung | fr | Stufe 3, Verzugszins, QR |
| 60 | Mahnung | de | neue Injection |
| 61 | Mahnung | it | Foto absichtlich unlesbar |
| 62 | unbekannt | de | Pfändungsankündigung |
| 63 | unbekannt | fr | provisorische Steuerrechnung (Acomptes) |
| 64 | unbekannt | it | Abstimmungsunterlagen, kein Betrag |
| 65 | unbekannt | de | Rechnung Feuerwehrersatzabgabe |

## Ausführen

```bash
python main.py _ --variante foto --daten daten/holdout
```

oder unter Windows `powershell -ExecutionPolicy Bypass -File .\laeufe.ps1 -Holdout`
(Protokolle: `daten/laeufe/<Datum>_holdout_foto_*.txt`).

Neu erzeugen: `cd datengenerator && python3 generator.py --holdout && python3 pruefe_gold.py --holdout`.
