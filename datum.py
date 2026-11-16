"""Datumsangaben aus Briefen deterministisch in ein date umwandeln.

Das LLM schreibt Daten so ab, wie sie im Brief stehen ("28.10.26", "21. September 2026",
"1er octobre 2026"). Die Umwandlung macht Python, nicht das Modell: Apertus hat beim
Umformatieren Jahreszahlen wie 2810 erfunden (aus 28.10.).
"""

import re
from datetime import date, datetime

# Plausibler Bereich für Daten auf einem Behördenbrief
JAHR_MIN, JAHR_MAX = 2000, 2099

MONATE = {
    # de
    "januar": 1, "jänner": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11,
    "dezember": 12,
    # fr
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "juin": 6,
    "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12, "decembre": 12,
    # it
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "dicembre": 12,
}


def parse_datum(wert) -> date:
    """str oder date -> date. Wirft ValueError bei unbekanntem Format oder unplausiblem Jahr."""
    if isinstance(wert, datetime):
        d = wert.date()
    elif isinstance(wert, date):
        d = wert
    elif isinstance(wert, str):
        d = _aus_text(wert)
    else:
        raise ValueError(f"Kein Datum: {wert!r}")
    if not JAHR_MIN <= d.year <= JAHR_MAX:
        raise ValueError(f"Unplausibles Datum: {d.isoformat()} (aus {wert!r})")
    return d


def _aus_text(s: str) -> date:
    s = s.strip().lower()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Datum mitten im Text, z. B. "Valmont, le 19 octobre 2026" oder "Talwil, 28.10.26"
    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})\b", s)
    if m:
        return date(_jahr(m.group(3)), int(m.group(2)), int(m.group(1)))
    # "21. September 2026", "1er octobre 2026", "3 settembre 2026"
    m = re.search(r"\b(\d{1,2})\s*(?:\.|er|°|º)?\s+([a-zäöüéèûàô]+)\s+(\d{4}|\d{2})\b", s)
    if m and m.group(2) in MONATE:
        return date(_jahr(m.group(3)), MONATE[m.group(2)], int(m.group(1)))
    raise ValueError(f"Unbekanntes Datumsformat: {s!r}")


def _jahr(text: str) -> int:
    jahr = int(text)
    return jahr + 2000 if jahr < 100 else jahr


def parse_datum_oder_none(wert, feld: str = "Datum") -> date | None:
    """Wie parse_datum, aber bei Fehler None plus Warnung statt Absturz.

    Lieber keine Frist (der Graph fragt dann nach) als eine Frist im Jahr 2810.
    """
    if wert is None or wert == "":
        return None
    try:
        return parse_datum(wert)
    except ValueError as fehler:
        print(f"  ! {feld} verworfen: {fehler}")
        return None
