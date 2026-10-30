"""Fristenrechner (Owner: Vendon) – deterministisch, ohne LLM.

Bewusst unabhängig von datengenerator/fristen.py geschrieben (sonst prüft die
Evaluation den Code gegen sich selbst). Umgesetzt nach Gesetzestext:

- SchKG Art. 31: Fristende auf Samstag, Sonntag oder Feiertag -> nächster Werktag
- SchKG Art. 56/63: Betreibungsferien (7 Tage vor/nach Ostern und Weihnachten,
  15.-31. Juli). Endet eine Frist darin, verlängert sie sich bis zum 3. Werktag
  nach Ende der Ferien. Gilt nur für den Zahlungsbefehl.
- Feiertage: nur die schweizweiten (siehe FEIERTAGE). Kantonale Feiertage fehlen bewusst;
  dadurch wird eine Frist höchstens zu früh, nie zu spät berechnet (konservativ).

TODO Vendon: Prüfung gegen Fedlex, Krankenkasse Zahlungsfrist der Prämie.
"""

from datetime import date, timedelta
from functools import lru_cache

from langchain_core.tools import tool

from state import ERINNERUNG_TAGE_VORHER

# Brieftyp -> Liste von (Fristart, Tage ab Zustellung, Basis, Rechtsgrundlage)
REGELN = {
    "zahlungsbefehl": [
        ("rechtsvorschlag", 10, "zustellung", "SchKG Art. 74"),
        ("zahlung", 20, "zustellung", "SchKG Art. 69"),
    ],
    "steuerveranlagung": [
        ("einsprache", 30, "tag_nach_zustellung", "DBG Art. 132"),
    ],
}


def ostersonntag(jahr: int) -> date:
    """Gregorianischer Ostersonntag (anonymer Gauss-Algorithmus)."""
    a, b, c = jahr % 19, jahr // 100, jahr % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    monat = (h + l - 7 * m + 114) // 31
    tag = (h + l - 7 * m + 114) % 31 + 1
    return date(jahr, monat, tag)


@lru_cache
def feiertage(jahr: int) -> frozenset[date]:
    """Schweizweite Feiertage. Kantonale (z. B. Berchtoldstag) bewusst nicht."""
    ostern = ostersonntag(jahr)
    return frozenset({
        date(jahr, 1, 1),                    # Neujahr
        ostern - timedelta(days=2),          # Karfreitag
        ostern + timedelta(days=1),          # Ostermontag
        ostern + timedelta(days=39),         # Auffahrt
        ostern + timedelta(days=50),         # Pfingstmontag
        date(jahr, 8, 1),                    # Bundesfeier
        date(jahr, 12, 25),                  # Weihnachten
        date(jahr, 12, 26),                  # Stephanstag
    })


def ist_werktag(d: date) -> bool:
    return d.weekday() < 5 and d not in feiertage(d.year)


def betreibungsferien(d: date) -> tuple[date, date] | None:
    """(Beginn, Ende) der Betreibungsferien, in die d fällt, sonst None (SchKG Art. 56)."""
    kandidaten = []
    for jahr in (d.year - 1, d.year):
        ostern = ostersonntag(jahr + 1)
        kandidaten.append((ostern - timedelta(days=7), ostern + timedelta(days=7)))
        weihnacht = date(jahr, 12, 25)
        kandidaten.append((weihnacht - timedelta(days=7), weihnacht + timedelta(days=7)))
    kandidaten.append((date(d.year, 7, 15), date(d.year, 7, 31)))
    for beginn, ende in kandidaten:
        if beginn <= d <= ende:
            return beginn, ende
    return None


def _fristende(ende: date, mit_betreibungsferien: bool) -> tuple[date, list[str]]:
    """Wendet SchKG Art. 31 und (beim Zahlungsbefehl) Art. 63 auf ein rechnerisches Fristende an."""
    hinweise: list[str] = []
    while True:
        ferien = betreibungsferien(ende) if mit_betreibungsferien else None
        if ferien:
            # bis zum 3. Tag nach Ende der Ferien; Sa, So und Feiertage zählen nicht mit
            d, gezaehlt = ferien[1], 0
            while gezaehlt < 3:
                d += timedelta(days=1)
                if ist_werktag(d):
                    gezaehlt += 1
            ende = d
            hinweise.append("betreibungsferien_verschoben")
            continue
        if not ist_werktag(ende):
            hinweis = "wochenende_verschoben" if ende.weekday() >= 5 else "feiertag_verschoben"
            while not ist_werktag(ende):
                ende += timedelta(days=1)
            hinweise.append(hinweis)
            continue
        return ende, list(dict.fromkeys(hinweise))


def _frist(art, datum, basis, ausgang=None, grundlage=None, hinweise=None) -> dict:
    return {
        "art": art, "datum": datum, "basis": basis, "ausgangsdatum": ausgang,
        "rechtsgrundlage": grundlage, "hinweise": hinweise or [],
        "erinnerung": datum - timedelta(days=ERINNERUNG_TAGE_VORHER),
    }

@tool
def fristen_berechnen(brieftyp: str, zustelldatum: date | None = None,
                      frist_im_brief: date | None = None,
                      zustelldatum_geschaetzt: bool = False) -> list[dict]:
    """Berechnet die Fristen eines Schweizer Behördenbriefs deterministisch.

    Für Zahlungsbefehl und Steuerveranlagung ab dem Zustelldatum, für Mahnung und
    Krankenkasse aus der Frist, die im Brief steht. Bei 'unbekannt' keine Frist.
    Nicht für Beträge oder Zinsen.
    """
    hinweis_zustellung = ["zustelldatum_geschaetzt"] if zustelldatum_geschaetzt else []

    if brieftyp in REGELN:
        if zustelldatum is None:
            return []  # ohne Zustelldatum keine Frist (Graph fragt vorher nach)
        fristen = []
        for art, tage, basis, grundlage in REGELN[brieftyp]:
            ende, hinweise = _fristende(zustelldatum + timedelta(days=tage),
                                        mit_betreibungsferien=(brieftyp == "zahlungsbefehl"))
            fristen.append(_frist(art, ende, basis, zustelldatum, grundlage,
                                  hinweise + hinweis_zustellung))
        return fristen

    if brieftyp == "mahnung" and frist_im_brief:
        return [_frist("zahlung", frist_im_brief, "brief")]  # Mahnfrist nicht verschoben

    if brieftyp == "krankenkasse_praemie" and frist_im_brief:
        # Annahme laut datengenerator/README: höhere Franchise bis 31.12. (vor Fedlex-Prüfung)
        return [
            _frist("kuendigung", frist_im_brief, "fixdatum", grundlage="KVG Art. 7 Abs. 2",
                   hinweise=["eingang_massgebend"]),
            _frist("franchise_wechsel", date(frist_im_brief.year, 12, 31), "fixdatum",
                   hinweise=["eingang_massgebend"]),
        ]

    return []
