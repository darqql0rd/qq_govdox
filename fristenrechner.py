"""Fristenrechner (Owner: Vendon) – deterministisch, ohne LLM.

Bewusst unabhängig von datengenerator/fristen.py geschrieben (sonst prüft die
Evaluation den Code gegen sich selbst). Umgesetzt nach Gesetzestext:

- SchKG Art. 31 i.V.m. ZPO Art. 142: Frist beginnt am Tag nach der Zustellung;
  Fristende auf Samstag, Sonntag oder Feiertag -> nächster Werktag.
  Ein Zahlungsbefehl, der am Samstag zugestellt wird, löst die Frist trotzdem aus
  (ZPO Art. 142 Abs. 1bis gilt nur für gewöhnliche Post; OG SH 16.12.2025).
- SchKG Art. 56/63: Betreibungsferien (7 Tage vor/nach Ostern und Weihnachten,
  15.-31. Juli). Endet eine Frist darin, verlängert sie sich bis zum 3. Tag nach Ende
  der Ferien; Sa, So und Feiertage zählen dabei nicht. Gilt nur für den Zahlungsbefehl.
- Zustellung WÄHREND der Betreibungsferien: wirkt erst am ersten Tag nach den Ferien
  (BGE 121 III 284 E. 2b, BGE 127 III 173 E. 3b). Erst ab dann läuft die Frist.
- Feiertage: Bundesrechtlich ist nur der 1. August Feiertag (BV Art. 110 Abs. 3), alle
  anderen legen die Kantone fest. Wir zählen nur Feiertage, die in (fast) allen Kantonen
  gelten (siehe feiertage()). Karfreitag (nicht TI, VS) und Stephanstag (nicht VS) fehlen
  deshalb bewusst. So wird eine Frist höchstens zu früh, nie zu spät berechnet.

Rechtsprüfung vom 09.11.2026: siehe Projekt-Doc "Fristen-Rechtspruefung".
Krankenkasse: Zahlungsfrist der Prämie nur, wenn sie im Brief steht (QR-Rechnung).
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
    """Feiertage, die in (fast) allen Kantonen gelten.

    Nicht enthalten, weil nicht überall Feiertag: Berchtoldstag, Karfreitag (nicht TI, VS),
    Stephanstag (nicht VS) und alle rein kantonalen Feiertage. Ostermontag und Pfingstmontag
    gelten nicht in allen Kantonen gleich (Wallis: Quellen widersprechen sich), bleiben aber
    drin, weil sie in fast der ganzen Schweiz gelten. Offen: gegen die BJ-Liste prüfen.
    """
    ostern = ostersonntag(jahr)
    return frozenset({
        date(jahr, 1, 1),                    # Neujahr
        ostern + timedelta(days=1),          # Ostermontag
        ostern + timedelta(days=39),         # Auffahrt
        ostern + timedelta(days=50),         # Pfingstmontag
        date(jahr, 8, 1),                    # Bundesfeier (BV Art. 110 Abs. 3)
        date(jahr, 12, 25),                  # Weihnachten
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


def wirksame_zustellung(zustelldatum: date, mit_betreibungsferien: bool) -> tuple[date, list[str]]:
    """Zustellung in den Betreibungsferien wirkt erst am ersten Tag nach den Ferien.

    BGE 121 III 284 E. 2b: weder nichtig noch anfechtbar, aber aufgeschobene Wirkung.
    Massgebend ist der Kalendertag nach Ferienende, auch wenn er ein Samstag oder
    Feiertag ist (BGE 113 III 5: 2. Januar). Die Frist beginnt am Tag danach.
    """
    ferien = betreibungsferien(zustelldatum) if mit_betreibungsferien else None
    if ferien is None:
        return zustelldatum, []
    return ferien[1] + timedelta(days=1), ["zustellung_in_betreibungsferien"]


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
                      zustelldatum_geschaetzt: bool = False,
                      zahlungsfrist_im_brief: date | None = None) -> list[dict]:
    """Berechnet die Fristen eines Schweizer Behördenbriefs deterministisch.

    Für Zahlungsbefehl und Steuerveranlagung ab dem Zustelldatum, für Mahnung und
    Krankenkasse aus der Frist, die im Brief steht (Krankenkasse: Kündigung, Franchise-Wechsel
    und, falls im Brief, die Zahlungsfrist der ersten Prämie). Bei 'unbekannt' keine Frist.
    Nicht für Beträge oder Zinsen.
    """
    hinweis_zustellung = ["zustelldatum_geschaetzt"] if zustelldatum_geschaetzt else []

    if brieftyp in REGELN:
        if zustelldatum is None:
            return []  # ohne Zustelldatum keine Frist (Graph fragt vorher nach)
        mit_ferien = brieftyp == "zahlungsbefehl"
        wirksam, hinweis_ferien = wirksame_zustellung(zustelldatum, mit_ferien)
        fristen = []
        for art, tage, basis, grundlage in REGELN[brieftyp]:
            ende, hinweise = _fristende(wirksam + timedelta(days=tage), mit_ferien)
            fristen.append(_frist(art, ende, basis, wirksam, grundlage,
                                  hinweis_ferien + hinweise + hinweis_zustellung))
        return fristen

    if brieftyp == "mahnung" and frist_im_brief:
        return [_frist("zahlung", frist_im_brief, "brief")]  # Mahnfrist nicht verschoben

    if brieftyp == "krankenkasse_praemie":
        fristen = []
        if frist_im_brief:
            # Annahme laut datengenerator/README: höhere Franchise bis 31.12. (vor Fedlex-Prüfung)
            fristen += [
                _frist("kuendigung", frist_im_brief, "fixdatum", grundlage="KVG Art. 7 Abs. 2",
                       hinweise=["eingang_massgebend"]),
                _frist("franchise_wechsel", date(frist_im_brief.year, 12, 31), "fixdatum",
                       hinweise=["eingang_massgebend"]),
            ]
        if zahlungsfrist_im_brief:
            # QR-Rechnung im Brief: "Prämie für Januar ... bis 31. Dezember zahlbar" (21, 25)
            fristen.append(_frist("zahlung", zahlungsfrist_im_brief, "brief"))
        return fristen

    return []
