"""Fristenrechner – PLATZHALTER für den Durchstich (Owner: Vendon).

Bewusst unabhängig von datengenerator/fristen.py geschrieben (sonst prüft die
Evaluation den Code gegen sich selbst).

Kann schon:   Fristlänge je Brieftyp, Verschiebung bei Samstag/Sonntag, Erinnerungsdatum.
TODO Vendon:  kantonale Feiertage (Hochwald/Haut-Lac/Valcastello), Betreibungsferien
              (Art. 56/63 SchKG), Prüfung gegen Fedlex, Krankenkasse franchise_wechsel.
"""

from datetime import date, timedelta

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


def _naechster_werktag(d: date) -> tuple[date, list[str]]:
    """Samstag/Sonntag -> Montag. TODO: Feiertage und Betreibungsferien."""
    hinweise = []
    while d.weekday() >= 5:
        d += timedelta(days=1)
        hinweise = ["wochenende_verschoben"]
    return d, hinweise


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
            ende, hinweise = _naechster_werktag(zustelldatum + timedelta(days=tage))
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
