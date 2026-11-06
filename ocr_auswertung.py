"""OCR-Auswertung: alle Testbriefe als PDF, Scan und Foto durch den OCR-Node schicken.

Misst die Ähnlichkeit OCR-Text zu text.txt (difflib, Leerraum normalisiert) und schreibt
die Tabelle für die Präsentation nach daten/ocr_auswertung.csv und .md.

    python ocr_auswertung.py                 # alle Briefe, alle Varianten
    python ocr_auswertung.py 01 11 --variante foto
"""

import argparse
import csv
import difflib
import time
from pathlib import Path

from mocks import DATEN, aus_gold, fall_ids, lade_gold
from nodes.ocr import MIN_WOERTER_PRO_SEITE, SCHWELLE_LESBAR, texterkennung

AUSGABE = Path("daten/ocr_auswertung")
VARIANTEN = ["pdf", "scan", "foto"]


def aehnlichkeit(a: str, b: str) -> float:
    a, b = " ".join(a.split()), " ".join(b.split())
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("muster", nargs="*")
    ap.add_argument("--variante", choices=VARIANTEN, action="append")
    args = ap.parse_args()
    varianten = args.variante or VARIANTEN
    faelle = [f for f in fall_ids() if not args.muster or any(f.startswith(m) or m in f for m in args.muster)]

    zeilen = []
    for fall in faelle:
        gold = lade_gold(fall)
        referenz = (DATEN / fall / "text.txt").read_text(encoding="utf-8")
        for variante in varianten:
            t = time.time()
            e = texterkennung(aus_gold(fall, variante)["dokument_pfade"])
            erwartet_lesbar = not (variante == "foto" and "unlesbar" in gold["testzweck"])
            zeile = {
                "fall": fall, "variante": variante, "textquelle": e["textquelle"],
                "seiten": e["seiten"], "zeichen": len(e["rohtext"]),
                "konfidenz": e["text_konfidenz"], "lesbar": e["text_lesbar"],
                "lesbar_erwartet": erwartet_lesbar,
                "aehnlichkeit": round(aehnlichkeit(referenz, e["rohtext"]), 3),
                "sekunden": round(time.time() - t, 1),
            }
            zeilen.append(zeile)
            print(" ".join(f"{k}={v}" for k, v in zeile.items()), flush=True)

    AUSGABE.parent.mkdir(exist_ok=True)
    with open(AUSGABE.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(zeilen[0]))
        w.writeheader()
        w.writerows(zeilen)
    schreibe_markdown(zeilen, varianten)


def schreibe_markdown(zeilen: list[dict], varianten: list[str]):
    md = ["# OCR-Auswertung", "",
          f"docTR (fast_base + PARSeq multilingual), Lesbarkeit: Konfidenz ≥ {SCHWELLE_LESBAR} "
          f"(mittlere Wortkonfidenz × min(1, Wörter / ({MIN_WOERTER_PRO_SEITE} × Seiten))). "
          "Ähnlichkeit = difflib.SequenceMatcher zu text.txt, Leerraum normalisiert.", "",
          "## Zusammenfassung", "",
          "| Variante | Briefe | Ø Ähnlichkeit | Median | Minimum | Lesbarkeit korrekt | Ø Sekunden |",
          "|---|---|---|---|---|---|---|"]
    for v in varianten:
        z = [r for r in zeilen if r["variante"] == v]
        if not z:
            continue
        # unlesbare Fotos nicht in den Durchschnitt (dort gibt es nichts zu vergleichen)
        s = sorted(r["aehnlichkeit"] for r in z if r["lesbar_erwartet"])
        richtig = sum(r["lesbar"] == r["lesbar_erwartet"] for r in z)
        md.append(f"| {v} | {len(z)} | {sum(s) / len(s):.3f} | {s[len(s) // 2]:.3f} | {s[0]:.3f} "
                  f"| {richtig}/{len(z)} | {sum(r['sekunden'] for r in z) / len(z):.1f} |")
    md += ["", "Ø, Median und Minimum ohne die absichtlich unlesbaren Fotos (11, 19, 36).", "",
           "## Pro Brief", "",
           "| Brief | " + " | ".join(f"{v} Ähnl. | {v} Konf. | {v} lesbar" for v in varianten) + " |",
           "|---|" + "---|---|---|" * len(varianten)]
    for fall in dict.fromkeys(r["fall"] for r in zeilen):
        zellen = []
        for v in varianten:
            r = next((r for r in zeilen if r["fall"] == fall and r["variante"] == v), None)
            if r is None:
                zellen += ["", "", ""]
                continue
            lesbar = ("ja" if r["lesbar"] else "nein") + ("" if r["lesbar"] == r["lesbar_erwartet"] else " ✗")
            konf = "–" if r["konfidenz"] is None else f"{r['konfidenz']:.2f}"
            zellen += [f"{r['aehnlichkeit']:.3f}", konf, lesbar]
        md.append(f"| {fall} | " + " | ".join(zellen) + " |")
    AUSGABE.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
