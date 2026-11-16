"""PDF-Rendering: 4 Layout-Vorlagen, Logos, Fusszeile, optionales Wasserzeichen, QR-Zahlteil."""
import os, io, math
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                Table, TableStyle, KeepTogether, PageBreak, NextPageTemplate)
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from pypdf import PdfReader, PdfWriter

HERE = os.path.dirname(os.path.abspath(__file__))
PW, PH = A4

# ------------------------------------------------------------------ Schriften
_LIB = "/usr/share/fonts/truetype/liberation/"
_DJV = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("LibSans", _LIB + "LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("LibSans-B", _LIB + "LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("LibSerif", _LIB + "LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("LibSerif-B", _LIB + "LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu", _DJV + "DejaVuSansCondensed.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-B", _DJV + "DejaVuSansCondensed-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Hand", os.path.join(HERE, "fonts", "Caveat-Regular.ttf")))

FONTS = {  # name: (regular, bold, Grundgrösse)
    "helv": ("Helvetica", "Helvetica-Bold", 9.5),
    "times": ("Times-Roman", "Times-Bold", 10.5),
    "libsans": ("LibSans", "LibSans-B", 9.5),
    "libserif": ("LibSerif", "LibSerif-B", 10.5),
    "dejavu": ("DejaVu", "DejaVu-B", 9.2),
}

WM = {"de": "MUSTER - SYNTHETISCH", "fr": "SPECIMEN - SYNTHETIQUE", "it": "FACSIMILE - SINTETICO"}
FOOT = {
    "de": "Synthetisches Testdokument: Personen, Behörden, Firmen, Adressen und Beträge sind frei erfunden. Keine Rechtswirkung.",
    "fr": "Document de test synthétique : personnes, autorités, entreprises, adresses et montants sont fictifs. Sans effet juridique.",
    "it": "Documento di prova sintetico: persone, autorità, ditte, indirizzi e importi sono fittizi. Senza effetto giuridico.",
}
PAGE = {"de": "Seite", "fr": "Page", "it": "Pagina"}

HAND_COLOR = "#1d3b8f"


def styles(font):
    reg, bold, base = FONTS[font]
    s = {
        "body": ParagraphStyle("body", fontName=reg, fontSize=base, leading=base * 1.38, spaceAfter=5),
        "small": ParagraphStyle("small", fontName=reg, fontSize=base - 1.6, leading=(base - 1.6) * 1.3),
        "tiny": ParagraphStyle("tiny", fontName=reg, fontSize=5.2, leading=6.4, textColor=colors.HexColor("#777777")),
        "light": ParagraphStyle("light", fontName=reg, fontSize=6.5, leading=8, textColor=colors.HexColor("#F3F3F3")),
        "sender": ParagraphStyle("sender", fontName=reg, fontSize=base - 1, leading=(base - 1) * 1.3),
        "senderb": ParagraphStyle("senderb", fontName=bold, fontSize=base + 0.5, leading=(base + 0.5) * 1.3),
        "addr": ParagraphStyle("addr", fontName=reg, fontSize=base + 0.5, leading=(base + 0.5) * 1.32),
        "title": ParagraphStyle("title", fontName=bold, fontSize=base + 3.8, leading=(base + 3.8) * 1.28, spaceAfter=4),
        "sub": ParagraphStyle("sub", fontName=bold, fontSize=base, leading=base * 1.35, spaceBefore=5, spaceAfter=3),
        "cell": ParagraphStyle("cell", fontName=reg, fontSize=base - 0.7, leading=(base - 0.7) * 1.3),
        "cellb": ParagraphStyle("cellb", fontName=bold, fontSize=base - 0.7, leading=(base - 0.7) * 1.3),
        "right": ParagraphStyle("right", fontName=reg, fontSize=base, leading=base * 1.38, alignment=2),
        "white": ParagraphStyle("white", fontName=bold, fontSize=base + 3, leading=(base + 3) * 1.25, textColor=colors.white),
        "whites": ParagraphStyle("whites", fontName=reg, fontSize=base - 1, leading=(base - 1) * 1.3, textColor=colors.white),
    }
    s["_reg"], s["_bold"] = reg, bold
    return s


# ------------------------------------------------------------------ Logos (abstrakt, keine Hoheitszeichen)
def draw_logo(c, x, y, size, logo, on_dark=False):
    shape, col, initials = logo["shape"], colors.HexColor(logo["color"]), logo.get("initials", "")
    c.saveState()
    if shape == "circle":
        c.setFillColor(colors.white if on_dark else col)
        c.circle(x + size / 2, y + size / 2, size / 2, stroke=0, fill=1)
        c.setFillColor(col if on_dark else colors.white)
        c.setFont("Helvetica-Bold", size * 0.36)
        c.drawCentredString(x + size / 2, y + size * 0.37, initials)
    elif shape == "mountain":
        c.setFillColor(colors.white if on_dark else col)
        p = c.beginPath(); p.moveTo(x, y); p.lineTo(x + size * 0.38, y + size * 0.85)
        p.lineTo(x + size * 0.55, y + size * 0.5); p.lineTo(x + size * 0.72, y + size * 0.72)
        p.lineTo(x + size, y); p.close(); c.drawPath(p, stroke=0, fill=1)
    elif shape == "wave":
        c.setStrokeColor(colors.white if on_dark else col); c.setLineWidth(size * 0.07)
        for k in range(3):
            p = c.beginPath(); yy = y + size * (0.25 + 0.25 * k)
            p.moveTo(x, yy)
            for i in range(1, 41):
                xx = x + size * i / 40
                p.lineTo(xx, yy + size * 0.08 * math.sin(i / 40 * 2 * math.pi * 1.5))
            c.drawPath(p, stroke=1, fill=0)
    elif shape == "square":
        c.setFillColor(colors.white if on_dark else col)
        c.roundRect(x, y, size, size, size * 0.18, stroke=0, fill=1)
        c.setFillColor(col if on_dark else colors.white)
        c.setFont("Helvetica-Bold", size * 0.34)
        c.drawCentredString(x + size / 2, y + size * 0.36, initials)
    elif shape == "leaf":
        c.setFillColor(colors.white if on_dark else col)
        p = c.beginPath(); p.moveTo(x + size * 0.1, y + size * 0.1)
        p.curveTo(x + size * 0.1, y + size * 0.9, x + size * 0.6, y + size, x + size * 0.95, y + size * 0.95)
        p.curveTo(x + size * 0.9, y + size * 0.4, x + size * 0.6, y + size * 0.05, x + size * 0.1, y + size * 0.1)
        c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


def _draw_par(c, html, style, x, ytop, w):
    p = Paragraph(html, style)
    _, h = p.wrapOn(c, w, 1000)
    p.drawOn(c, x, ytop - h)
    return h


def _draw_lines(c, lines, st, x, ytop, w, first_bold=True):
    y = ytop
    for i, l in enumerate(lines):
        y -= _draw_par(c, l, st["senderb"] if (i == 0 and first_bold) else st["sender"], x, y, w)
    return ytop - y


# ------------------------------------------------------------------ Tabellen & Boxen
def make_table(st, rows, fracs, width, header=False, total_last=False, right_cols=()):
    data = []
    for i, r in enumerate(rows):
        b = (header and i == 0) or (total_last and i == len(rows) - 1)
        row = []
        for j, v in enumerate(r):
            base = st["cellb" if b else "cell"]
            if j in right_cols:
                base = ParagraphStyle("r", parent=base, alignment=2)
            row.append(Paragraph(v, base) if isinstance(v, str) else v)
        data.append(row)
    t = Table(data, colWidths=[f * width for f in fracs])
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#BBBBBB")),
             ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
             ("LEFTPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECECEC")))
    if total_last:
        style.append(("LINEABOVE", (0, -1), (-1, -1), 0.9, colors.black))
    t.setStyle(TableStyle(style))
    return t


def box(st, lines, width, title=None):
    content = [Paragraph(title, st["sub"])] if title else []
    content += [Paragraph(l, st["cell"]) for l in lines]
    t = Table([[content]], colWidths=[width])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
    return t


def hand(text, size=15):
    return f'<font name="Hand" size="{size}" color="{HAND_COLOR}">{text}</font>'


# ------------------------------------------------------------------ Hauptfunktion
def build_pdf(spec, path):
    st = styles(spec["font"])
    lang, tpl = spec["lang"], spec["template"]
    logo = spec["logo"]
    sender = spec["sender"]
    accent = colors.HexColor(logo["color"])

    # Rahmen je Vorlage
    if tpl == "C":
        fx, fw = 64 * mm, 126 * mm
    else:
        fx, fw = 20 * mm, 170 * mm
    first_top = {"A": PH - 42 * mm, "B": PH - 38 * mm, "C": PH - 18 * mm, "D": PH - 40 * mm}[tpl]
    bottom = 20 * mm

    def footer(c, doc):
        c.saveState()
        c.setFont(st["_reg"], 6.6); c.setFillColor(colors.HexColor("#666666"))
        c.drawString(20 * mm, 10 * mm, FOOT[lang])
        c.drawRightString(190 * mm, 10 * mm, f"{PAGE[lang]} {doc.page}")
        c.restoreState()
        if spec.get("watermark"):
            c.saveState()
            c.setFont("Helvetica-Bold", 46)
            c.setFillColor(colors.Color(0.82, 0.82, 0.82, alpha=0.35))
            c.translate(105 * mm, 150 * mm); c.rotate(35)
            c.drawCentredString(0, 0, WM[lang])
            c.restoreState()

    def first_page(c, doc):
        if tpl == "A":
            _draw_lines(c, sender, st, 20 * mm, PH - 14 * mm, 105 * mm)
            draw_logo(c, 170 * mm, PH - 32 * mm, 20 * mm, logo)
        elif tpl == "B":
            draw_logo(c, 20 * mm, PH - 30 * mm, 16 * mm, logo)
            _draw_lines(c, sender, st, 40 * mm, PH - 14 * mm, 110 * mm)
            c.setStrokeColor(accent); c.setLineWidth(1.4)
            c.line(20 * mm, PH - 34 * mm, 190 * mm, PH - 34 * mm)
        elif tpl == "C":
            c.saveState(); c.setFillColor(colors.HexColor("#F1F1EE"))
            c.rect(0, 0, 56 * mm, PH, stroke=0, fill=1)
            c.setFillColor(accent); c.rect(0, PH - 6 * mm, 56 * mm, 6 * mm, stroke=0, fill=1)
            c.restoreState()
            draw_logo(c, 12 * mm, PH - 36 * mm, 22 * mm, logo)
            y = PH - 44 * mm
            y -= _draw_lines(c, sender, st, 10 * mm, y, 42 * mm) + 8 * mm
            for lab, val in spec.get("refs", []):
                y -= _draw_par(c, f"<b>{lab}</b>", st["small"], 10 * mm, y, 42 * mm)
                y -= _draw_par(c, val, st["small"], 10 * mm, y, 42 * mm) + 2.5 * mm
        elif tpl == "D":
            c.saveState(); c.setFillColor(accent)
            c.rect(0, PH - 26 * mm, PW, 26 * mm, stroke=0, fill=1); c.restoreState()
            draw_logo(c, 20 * mm, PH - 21 * mm, 16 * mm, logo, on_dark=True)
            _draw_par(c, sender[0], st["white"], 42 * mm, PH - 8 * mm, 140 * mm)
            _draw_par(c, " · ".join(sender[1:]), st["whites"], 42 * mm, PH - 16 * mm, 148 * mm)
        footer(c, doc)

    doc = BaseDocTemplate(path, pagesize=A4, title=spec["title_plain"], author="Synthetischer Testdatensatz",
                          subject=spec["id"])
    f1 = Frame(fx, bottom, fw, first_top - bottom, id="f1", leftPadding=0, rightPadding=0, topPadding=0)
    f2 = Frame(20 * mm, bottom, 170 * mm, PH - 20 * mm - bottom, id="f2", leftPadding=0, rightPadding=0)
    doc.addPageTemplates([PageTemplate("first", [f1], onPage=first_page),
                          PageTemplate("later", [f2], onPage=footer)])
    W = fw
    story = [NextPageTemplate("later")]

    # Adressblock
    addr = [Paragraph(x, st["addr"]) for x in spec["recipient"]]
    if tpl in ("A", "D"):
        story.append(Table([["", addr]], colWidths=[W - 78 * mm, 78 * mm],
                           style=[("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    elif tpl == "B":
        refs = [[Paragraph(f"<b>{a}</b>", st["small"]), Paragraph(b, st["small"])] for a, b in spec.get("refs", [])]
        rt = Table(refs, colWidths=[30 * mm, 50 * mm],
                   style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0.6),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6)]) if refs else ""
        story.append(Table([[addr, rt]], colWidths=[W - 82 * mm, 82 * mm],
                           style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    else:  # C
        story.append(Spacer(1, 22 * mm))
        story.append(Table([[addr]], colWidths=[W], style=[("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(Spacer(1, 10 * mm if tpl != "C" else 14 * mm))
    story.append(Paragraph(spec["place_date"], st["right"]))
    if tpl in ("A", "D") and spec.get("refs"):
        rows = [[Paragraph(a, st["small"]), Paragraph(b, st["small"])] for a, b in spec["refs"]]
        rt = Table(rows, colWidths=[38 * mm, W - 38 * mm])
        ts = [("LEFTPADDING", (0, 0), (-1, -1), 0 if tpl == "A" else 4), ("TOPPADDING", (0, 0), (-1, -1), 0.6),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6)]
        if tpl == "D":
            ts += [("BOX", (0, 0), (-1, -1), 0.6, accent), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F7F7"))]
        rt.setStyle(TableStyle(ts))
        story.append(rt)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(spec["title"], st["title"]))

    footnotes = []
    for item in spec["body"]:
        k = item[0]
        if k == "p":
            story.append(Paragraph(item[1], st["body"]))
        elif k == "h":
            story.append(Paragraph(item[1], st["sub"]))
        elif k == "t":
            opts = item[3] if len(item) > 3 else {}
            story.append(make_table(st, item[1], item[2], W, **opts))
            story.append(Spacer(1, 3.5 * mm))
        elif k == "box":
            story.append(Spacer(1, 1.5 * mm))
            story.append(box(st, item[1], W, item[2] if len(item) > 2 else None))
            story.append(Spacer(1, 3.5 * mm))
        elif k == "sp":
            story.append(Spacer(1, item[1] * mm))
        elif k == "pb":
            story.append(PageBreak())
        elif k == "light":           # Injection: fast unsichtbarer Text
            story.append(Paragraph(item[1], st["light"]))
        elif k == "tiny":            # Kleingedrucktes
            story.append(Paragraph(item[1], st["tiny"]))
        elif k == "footnote":        # Fussnote am Briefende
            footnotes.append(item[1])
    story.append(Spacer(1, 5 * mm))
    story.append(KeepTogether([Paragraph(x, st["body"]) for x in spec["sign"]]))
    for fn in footnotes:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(fn, ParagraphStyle("fn", parent=st["tiny"], fontSize=6.2, leading=7.6)))
    doc.build(story)

    if spec.get("qr"):
        buf = io.BytesIO()
        qr_page(buf, spec, st)
        w = PdfWriter()
        for pg in PdfReader(path).pages:
            w.add_page(pg)
        for pg in PdfReader(io.BytesIO(buf.getvalue())).pages:
            w.add_page(pg)
        w.add_metadata({"/Title": spec["title_plain"], "/Subject": spec["id"]})
        with open(path, "wb") as fh:
            w.write(fh)


# ------------------------------------------------------------------ QR-Zahlteil (Layout nach Schweizer QR-Rechnung, nicht zahlbar)
QRT = {
    "de": dict(receipt="Empfangsschein", pay="Zahlteil", acct="Konto / Zahlbar an", ref="Referenz",
               add="Zusätzliche Informationen", by="Zahlbar durch", cur="Währung", amt="Betrag",
               accept="Annahmestelle", head="Zahlteil zu unserem Schreiben vom {d}",
               note="Bitte verwenden Sie für die Zahlung den untenstehenden Zahlteil. (Synthetisches Muster: die Kontoangaben sind ungültig.)"),
    "fr": dict(receipt="Récépissé", pay="Section paiement", acct="Compte / Payable à", ref="Référence",
               add="Informations supplémentaires", by="Payable par", cur="Monnaie", amt="Montant",
               accept="Point de dépôt", head="Section paiement relative à notre courrier du {d}",
               note="Veuillez utiliser la section paiement ci-dessous. (Modèle synthétique : les coordonnées bancaires sont invalides.)"),
    "it": dict(receipt="Ricevuta", pay="Sezione pagamento", acct="Conto / Pagabile a", ref="Riferimento",
               add="Informazioni supplementari", by="Pagabile da", cur="Valuta", amt="Importo",
               accept="Punto di accettazione", head="Sezione pagamento relativa al nostro scritto del {d}",
               note="Per il pagamento utilizzi la sezione sottostante. (Modello sintetico: i dati del conto non sono validi.)"),
}


def qr_page(buf, spec, st):
    lang, q = spec["lang"], spec["qr"]
    T = QRT[lang]
    c = rl_canvas.Canvas(buf, pagesize=A4)
    # Kopf
    draw_logo(c, 20 * mm, PH - 32 * mm, 14 * mm, spec["logo"])
    _draw_lines(c, spec["sender"][:3], st, 38 * mm, PH - 18 * mm, 120 * mm)
    _draw_par(c, f"<b>{T['head'].format(d=q['bezug_datum'])}</b>", st["body"], 20 * mm, PH - 50 * mm, 170 * mm)
    _draw_par(c, T["note"], st["body"], 20 * mm, PH - 58 * mm, 170 * mm)
    c.setFont(st["_reg"], 6.6); c.setFillColor(colors.HexColor("#666666"))
    c.drawString(20 * mm, 112 * mm, FOOT[lang]); c.setFillColor(colors.black)

    # Perforation
    c.setDash(2, 2); c.setLineWidth(0.4)
    c.line(0, 105 * mm, PW, 105 * mm); c.line(62 * mm, 0, 62 * mm, 105 * mm); c.setDash()

    def head(x, y, t):
        c.setFont("Helvetica-Bold", 6); c.drawString(x, y, t)

    def val(x, y, lines, size=8):
        c.setFont("Helvetica", size)
        for i, l in enumerate(lines):
            c.drawString(x, y - i * (size + 1.2), l)
        return y - len(lines) * (size + 1.2)

    amt = q["betrag"]
    amt_s = f"{amt:,.2f}".replace(",", " ") if amt is not None else ""
    # Empfangsschein
    x = 5 * mm; y = 105 * mm - 9 * mm
    c.setFont("Helvetica-Bold", 11); c.drawString(x, y, T["receipt"]); y -= 7 * mm
    head(x, y, T["acct"]); y = val(x, y - 9, [q["konto"]] + q["empfaenger"]) - 4
    head(x, y, T["ref"]); y = val(x, y - 9, [q["referenz"]]) - 4
    head(x, y, T["by"]); val(x, y - 9, q["zahler"])
    head(x, 37 * mm, T["cur"]); head(x + 14 * mm, 37 * mm, T["amt"])
    c.setFont("Helvetica", 8); c.drawString(x, 37 * mm - 10, "CHF"); c.drawString(x + 14 * mm, 37 * mm - 10, amt_s)
    head(38 * mm, 18 * mm, T["accept"])

    # Zahlteil
    x = 67 * mm
    c.setFont("Helvetica-Bold", 11); c.drawString(x, 105 * mm - 9 * mm, T["pay"])
    payload = "\r\n".join(["SPC", "0200", "1", q["konto"].replace(" ", ""), "S"] + q["empfaenger"][:1] +
                          ["", "", "", "", "CH", "", "", "", "", "", "", "", f"{amt:.2f}" if amt else "", "CHF",
                           "", "", "", "", "", "", "", "NON", q["referenz"].replace(" ", ""),
                           "SYNTHETISCHES TESTDOKUMENT - KEINE ZAHLUNG", "EPD"])
    w = QrCodeWidget(payload, barLevel="M")
    b = w.getBounds(); bw, bh = b[2] - b[0], b[3] - b[1]
    size = 46 * mm
    d = Drawing(size, size, transform=[size / bw, 0, 0, size / bh, 0, 0]); d.add(w)
    renderPDF.draw(d, c, x, 105 * mm - 17 * mm - size)
    cx, cy = x + size / 2, 105 * mm - 17 * mm - size / 2
    c.setFillColor(colors.white); c.rect(cx - 3.9 * mm, cy - 3.9 * mm, 7.8 * mm, 7.8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.black); c.rect(cx - 3.5 * mm, cy - 3.5 * mm, 7 * mm, 7 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.rect(cx - 0.7 * mm, cy - 2.3 * mm, 1.4 * mm, 4.6 * mm, stroke=0, fill=1)
    c.rect(cx - 2.3 * mm, cy - 0.7 * mm, 4.6 * mm, 1.4 * mm, stroke=0, fill=1)
    c.setFillColor(colors.black)
    head(x, 37 * mm, T["cur"]); head(x + 14 * mm, 37 * mm, T["amt"])
    c.setFont("Helvetica", 10); c.drawString(x, 37 * mm - 12, "CHF"); c.drawString(x + 14 * mm, 37 * mm - 12, amt_s)
    x = 118 * mm; y = 105 * mm - 9 * mm
    head(x, y, T["acct"]); y = val(x, y - 10, [q["konto"]] + q["empfaenger"], 10) - 5
    head(x, y, T["ref"]); y = val(x, y - 10, [q["referenz"]], 10) - 5
    head(x, y, T["add"]); y = val(x, y - 10, q["zusatz"], 10) - 5
    head(x, y, T["by"]); val(x, y - 10, q["zahler"], 10)
    c.showPage(); c.save()
