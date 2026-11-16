"""Fristenrechner testen, ohne LLM und ohne Graph.

1. Regression: Alle Testbriefe mit gesetzlicher Frist (Zahlungsbefehl, Steuer) gegen
   die erwarteten Fristen in gold.json.
2. Rechtsfälle aus der Rechtsprüfung vom 09.11.2026 (Projekt-Doc "Fristen-Rechtspruefung"):
   Fälle, die im Datensatz fehlen, mit Begründung.

    python tests/teste_fristenrechner.py
"""

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fristenrechner import REGELN, feiertage, fristen_berechnen  # noqa: E402
from state import Frist  # noqa: E402

BRIEFE = ROOT / "daten" / "briefe"

# (Name, Brieftyp, Zustelldatum, {Fristart: erwartetes Datum}, erwartete Hinweise, Begründung)
RECHTSFAELLE = [
    ("Zustellung in den Weihnachts-Betreibungsferien", "zahlungsbefehl", date(2026, 12, 22),
     {"rechtsvorschlag": date(2027, 1, 12), "zahlung": date(2027, 1, 22)},
     {"zustellung_in_betreibungsferien"},
     "Ferien 18.12.-01.01., Wirkung am 02.01. (BGE 121 III 284), +10 bzw. +20 Tage"),
    ("Zustellung in den Oster-Betreibungsferien", "zahlungsbefehl", date(2026, 4, 1),
     {"rechtsvorschlag": date(2026, 4, 23), "zahlung": date(2026, 5, 4)},
     {"zustellung_in_betreibungsferien"},
     "Ferien 29.03.-12.04., Wirkung am 13.04.; 03.05. ist ein Sonntag -> 04.05."),
    ("Zustellung am letzten Ferientag", "zahlungsbefehl", date(2026, 7, 31),
     {"rechtsvorschlag": date(2026, 8, 11)},
     {"zustellung_in_betreibungsferien"},
     "Wirkung am 01.08. (Samstag, Bundesfeier) - massgebend ist der Kalendertag"),
    ("Zustellung am Tag nach den Ferien", "zahlungsbefehl", date(2026, 8, 1),
     {"rechtsvorschlag": date(2026, 8, 11)},
     set(),
     "keine Verschiebung des Fristbeginns"),
    ("Zahlungsbefehl am Samstag zugestellt", "zahlungsbefehl", date(2025, 11, 8),
     {"rechtsvorschlag": date(2025, 11, 18)},
     set(),
     "Frist beginnt am Sonntag (OG SH 16.12.2025)"),
    ("Steuer: Fristende am Karfreitag", "steuerveranlagung", date(2026, 3, 4),
     {"einsprache": date(2026, 4, 3)},
     set(),
     "Karfreitag ist in TI und VS kein Feiertag -> nicht verschieben (sonst zu spät)"),
    ("Steuer: Fristende am Stephanstag", "steuerveranlagung", date(2025, 11, 26),
     {"einsprache": date(2025, 12, 26)},
     set(),
     "Stephanstag ist in VS kein Feiertag -> nicht verschieben"),
    ("Steuer: Fristende an Weihnachten", "steuerveranlagung", date(2026, 11, 25),
     {"einsprache": date(2026, 12, 28)},
     {"feiertag_verschoben"},
     "25.12. Feiertag, 26.+27.12. Wochenende"),
    ("Steuer in den Ferien zugestellt: keine Betreibungsferien", "steuerveranlagung",
     date(2026, 12, 22), {"einsprache": date(2027, 1, 21)}, set(),
     "Art. 56/63 SchKG gelten nur im Betreibungsverfahren"),
]


def rechne(brieftyp: str, zustelldatum: date) -> list[Frist]:
    roh = fristen_berechnen.invoke({"brieftyp": brieftyp, "zustelldatum": zustelldatum})
    return [Frist(**f) for f in roh]  # prüft auch, dass die Hinweise im Schema erlaubt sind


def teste_gold() -> int:
    fehler = 0
    anzahl = 0
    for datei in sorted(BRIEFE.glob("*/gold.json")):
        gold = json.loads(datei.read_text(encoding="utf-8"))
        if gold["brieftyp"] not in REGELN:
            continue
        zustellung = (gold["extraktion"].get("zustelldatum_im_brief")
                      or gold.get("zustelldatum_annahme"))
        if not zustellung:
            continue
        anzahl += 1
        erwartet = {f["art"]: f["datum"] for f in gold["erwartete_fristen"]}
        for f in rechne(gold["brieftyp"], date.fromisoformat(zustellung)):
            if erwartet.get(f.art) != f.datum.isoformat():
                fehler += 1
                print(f"  ✗ {gold['id']} {f.art}: erwartet {erwartet.get(f.art)}, erhalten {f.datum}")
    print(f"Gold: {anzahl} Briefe geprüft, {fehler} Abweichungen")
    return fehler


def teste_rechtsfaelle() -> int:
    fehler = 0
    for name, typ, zustellung, erwartet, hinweise, grund in RECHTSFAELLE:
        fristen = {f.art: f for f in rechne(typ, zustellung)}
        probleme = [f"{art}: erwartet {d}, erhalten {fristen[art].datum}"
                    for art, d in erwartet.items() if fristen[art].datum != d]
        alle_hinweise = set().union(*(f.hinweise for f in fristen.values()))
        if "zustellung_in_betreibungsferien" in hinweise ^ alle_hinweise:
            probleme.append(f"Hinweise: {sorted(alle_hinweise)}")
        if not hinweise <= alle_hinweise:
            probleme.append(f"Hinweise fehlen: {sorted(hinweise - alle_hinweise)}")
        print(f"  {'✗' if probleme else '✓'} {name} ({grund})")
        for p in probleme:
            print(f"      {p}")
        fehler += bool(probleme)
    return fehler


def teste_feiertage() -> int:
    """Nur Feiertage, die in allen Kantonen gelten (sonst kann eine Frist zu spät werden)."""
    ostern_2026 = date(2026, 4, 5)
    verboten = {date(2026, 4, 3): "Karfreitag", date(2026, 12, 26): "Stephanstag",
                date(2026, 1, 2): "Berchtoldstag"}
    fehler = [n for d, n in verboten.items() if d in feiertage(2026)]
    if date(2026, 8, 1) not in feiertage(2026) or ostern_2026 in feiertage(2026):
        fehler.append("Grundgerüst")
    print(f"  {'✗ ' + ', '.join(fehler) if fehler else '✓'} Feiertagsliste ohne kantonale Feiertage")
    return len(fehler)


def teste_krankenkasse() -> int:
    """Kündigung und Franchise aus frist_im_brief, Zahlung nur mit zahlungsfrist_im_brief (21/25)."""
    def arten(**kw):
        roh = fristen_berechnen.invoke({"brieftyp": "krankenkasse_praemie", **kw})
        return {f["art"]: f["datum"] for f in roh}
    ohne_qr = arten(frist_im_brief=date(2026, 11, 30))
    mit_qr = arten(frist_im_brief=date(2026, 11, 30), zahlungsfrist_im_brief=date(2026, 12, 31))
    nur_zahlung = arten(zahlungsfrist_im_brief=date(2026, 12, 31))
    ok = (ohne_qr == {"kuendigung": date(2026, 11, 30), "franchise_wechsel": date(2026, 12, 31)}
          and mit_qr == {**ohne_qr, "zahlung": date(2026, 12, 31)}
          and nur_zahlung == {"zahlung": date(2026, 12, 31)})
    print(f"  {'✓' if ok else '✗'} Krankenkasse: Zahlungsfrist nur, wenn sie im Brief steht")
    return 0 if ok else 1


if __name__ == "__main__":
    print("Rechtsfälle:")
    total = teste_rechtsfaelle() + teste_feiertage() + teste_krankenkasse()
    total += teste_gold()
    print("Alle Tests bestanden" if total == 0 else f"{total} Fehler")
    sys.exit(1 if total else 0)
