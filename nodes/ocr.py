"""OCR-Node (Owner: Nayan) – PLATZHALTER aus dem Graph-Gerüst.

Reicht den Rohtext durch, den main.py heute aus text.txt mitgibt, und zählt den
Versuch. Schreibt nur seine Felder aus FELDER_PRO_NODE["ocr"].
Wird durch den echten Node (pypdf / Tesseract) ersetzt.
"""

from state import MAX_VERSUCHE, BriefState


def ocr(state: BriefState) -> dict:
    lesbar = state.get("text_lesbar", bool(state.get("rohtext")))
    update = {
        "textquelle": state.get("textquelle", "pdf_text"),
        "rohtext": state.get("rohtext", ""),
        "seiten": state.get("seiten", len(state.get("dokument_pfade", [])) or 1),
        "text_lesbar": lesbar,
        "text_konfidenz": state.get("text_konfidenz"),
        "versuche": {"ocr": 1},  # der Reducer zählt zusammen
    }
    # Letzter Versuch und immer noch unlesbar: Abbruch hier setzen, das Routing schreibt nichts
    if not lesbar and state.get("versuche", {}).get("ocr", 0) + 1 >= MAX_VERSUCHE["ocr"]:
        update["abbruch_grund"] = "unlesbar"
    return update
