"""OCR-Node (Owner: Nayan): Text aus PDF-Textebene oder Foto/Scan (docTR).

Ist rohtext schon im State (main.py --variante pdf), wird er nur durchgereicht.

Bewusste Entscheide:
- docTR statt Tesseract (Alternative laut Arbeitsplan; Tesseract liess sich unter macOS
  nicht installieren). docTR hat keinen lang-Parameter wie Tesseract; das Standardmodell
  kennt kein ä/ö. Darum das mehrsprachige PARSeq-Modell von Hugging Face (DE/FR/IT).
- Handyfotos sind leicht schräg. docTR richtet die Seite zuerst gerade (straighten_pages)
  und schneidet die Wörter danach achsenparallel aus (assume_straight_pages=True).
  Mit schrägen Wortboxen dreht docTR kurze Wörter oft auf den Kopf ("innert 20" ->
  "innert OZ", "15 ottobre" -> "SI ottobre"), was die Fristen kaputt macht.
- Das Modell wird nur einmal geladen (lazy, gecacht), nicht pro Brief.
"""

import os
import re
from functools import cache
from pathlib import Path

from pypdf import PdfReader

from state import MAX_VERSUCHE, BriefState

RECO_MODELL = "Felix92/doctr-torch-parseq-multilingual-v1"

# Lesbarkeit: kalibriert auf den 45 Testbriefen (siehe daten/ocr_auswertung.md).
# text_konfidenz = mittlere Wortkonfidenz x Anteil an MIN_WOERTER_PRO_SEITE (gedeckelt bei 1).
# Unlesbare Fotos haben oft noch hohe Wortkonfidenz, aber kaum erkannte Wörter
# (Brief 19: ~53 Wörter/Seite). Pro Seite, weil kurze Briefe (Werbung, Busse) nur
# ~100 Wörter auf einer Seite haben; Seite 2 des Zahlungsbefehls hat nur ~30.
MIN_WOERTER_PRO_SEITE = 80
SCHWELLE_LESBAR = 0.75

# Ab so vielen Zeichen gilt die PDF-Textebene als vorhanden (sonst gescanntes PDF -> OCR)
MIN_ZEICHEN_PDF = 50

# Wasserzeichen der Testbriefe (datengenerator/render.py), in der PDF-Textebene wörtlich
# enthalten. Im Foto ist es so blass, dass docTR es meist gar nicht liest.
WASSERZEICHEN = re.compile(
    r"\b(MUSTER|SP[EÉ]CIMEN|FAC-?SIMILE)\s*[-–—]\s*(SYNTHETISCH|SYNTH[EÉ]TIQUE|SINTETICO)\b",
    re.IGNORECASE,
)


@cache
def _modell():
    # python.org-Python unter macOS findet die Systemzertifikate nicht -> Modell-Download
    # schlägt fehl. certifi kommt mit den Abhängigkeiten von docTR mit.
    if "SSL_CERT_FILE" not in os.environ:
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()

    from doctr.models import from_hub, ocr_predictor  # spät importieren: torch lädt lange

    return ocr_predictor(
        det_arch="fast_base",
        reco_arch=from_hub(RECO_MODELL),
        pretrained=True,
        assume_straight_pages=True,   # gilt nach dem Geraderichten
        detect_orientation=True,
        straighten_pages=True,
    )


def wasserzeichen_entfernen(text: str) -> str:
    zeilen = []
    for zeile in text.splitlines():
        ohne = WASSERZEICHEN.sub("", zeile)
        if ohne.strip() or ohne == zeile:  # Zeile, die nur aus dem Wasserzeichen bestand, weg
            zeilen.append(ohne)
    return "\n".join(zeilen)


def _pdf_text(pfad: Path) -> str:
    return "\n".join(seite.extract_text() or "" for seite in PdfReader(pfad).pages)


def _ocr(seiten) -> tuple[str, list[float]]:
    """docTR auf eine Liste von Seitenbildern; gibt Text und Wortkonfidenzen zurück."""
    doc = _modell()(seiten)
    konfidenzen = [w.confidence for p in doc.pages for b in p.blocks
                   for z in b.lines for w in z.words]
    return doc.render(), konfidenzen


def texterkennung(pfade: list[str]) -> dict:
    """Text aus allen Seiten (eine Datei pro Seite, PDFs auch mehrseitig).

    Gibt die State-Felder der Texterkennung zurück, ohne Versuchszähler.
    """
    from doctr.io import DocumentFile

    texte, konfidenzen, seiten, ocr_genutzt = [], [], 0, False
    for p in map(Path, pfade):
        if p.suffix.lower() == ".pdf":
            text = _pdf_text(p)
            if len(text.strip()) >= MIN_ZEICHEN_PDF:
                texte.append(text)
                seiten += len(PdfReader(p).pages)
                continue
            bilder = DocumentFile.from_pdf(p)  # PDF ohne Textebene (gescannt)
        else:
            bilder = DocumentFile.from_images([p])
        text, k = _ocr(bilder)
        texte.append(text)
        konfidenzen += k
        seiten += len(bilder)
        ocr_genutzt = True

    rohtext = wasserzeichen_entfernen("\n\n".join(texte))
    if not ocr_genutzt:
        return {"textquelle": "pdf_text", "rohtext": rohtext, "seiten": seiten,
                "text_lesbar": bool(rohtext), "text_konfidenz": None}

    mittel = sum(konfidenzen) / len(konfidenzen) if konfidenzen else 0.0
    konfidenz = round(mittel * min(1.0, len(konfidenzen) / (MIN_WOERTER_PRO_SEITE * seiten)), 3)
    return {"textquelle": "ocr", "rohtext": rohtext, "seiten": seiten,
            "text_lesbar": konfidenz >= SCHWELLE_LESBAR, "text_konfidenz": konfidenz}


def ocr(state: BriefState) -> dict:
    if state.get("rohtext"):
        # Rohtext schon vorhanden (python main.py --variante pdf liefert text.txt) -> kein OCR
        update = {"textquelle": state.get("textquelle", "pdf_text"), "rohtext": state["rohtext"],
                  "seiten": state.get("seiten", len(state.get("dokument_pfade", [])) or 1),
                  "text_lesbar": state.get("text_lesbar", True),
                  "text_konfidenz": state.get("text_konfidenz")}
    else:
        update = texterkennung(state["dokument_pfade"])
    update["versuche"] = {"ocr": 1}  # Reducer zählt zusammen
    versuche = state.get("versuche", {}).get("ocr", 0) + 1
    if not update["text_lesbar"] and versuche >= MAX_VERSUCHE["ocr"]:
        update["abbruch_grund"] = "unlesbar"
    return update
