"""Guide d'utilisation SAV Service Tool (PDF).  Usage : py make_pdf.py <dossier_captures> <fichier.pdf>

Le sommaire est calculé : le document est construit deux fois, la première pour relever les numéros de page.
"""
import sys
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

SHOTS = Path(sys.argv[1])
OUT = Path(sys.argv[2])
VERSION = "2.0.1"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import story  # noqa: E402
F = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("UI", F + r"\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("UI-B", F + r"\segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("UI-I", F + r"\segoeuii.ttf"))
pdfmetrics.registerFont(TTFont("UI-SB", F + r"\seguisb.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + r"\consola.ttf"))
registerFontFamily("UI", normal="UI", bold="UI-B", italic="UI-I", boldItalic="UI-B")

# Couleurs de SAV Service Tool (identiques à l'application)
TEAL = colors.HexColor("#2F6FED")
TEAL_DARK = colors.HexColor("#16213A")
BLACK = colors.HexColor("#16213A")
INK = colors.HexColor("#1F2328")
MUTED = colors.HexColor("#59636E")
LINE = colors.HexColor("#D0D7DE")
SOFT = colors.HexColor("#F5F6F8")
TIP_BG = colors.HexColor("#EAF1FE")
WARN_BG = colors.HexColor("#FDEFE6"); WARN_BD = colors.HexColor("#E8590C")
INFO_BG = colors.HexColor("#EEF2F7"); INFO_BD = colors.HexColor("#59636E")

ss = {}
ss["body"] = ParagraphStyle("body", fontName="UI", fontSize=10, leading=14.5, textColor=INK, spaceAfter=6)
ss["h1"] = ParagraphStyle("h1", fontName="UI-B", fontSize=20, leading=25, textColor=INK, spaceBefore=2, spaceAfter=6)
ss["kicker"] = ParagraphStyle("kicker", fontName="UI-SB", fontSize=9.5, leading=12, textColor=TEAL_DARK, spaceAfter=2)
ss["h2"] = ParagraphStyle("h2", fontName="UI-B", fontSize=13, leading=17, textColor=INK, spaceBefore=12, spaceAfter=5)
ss["h3"] = ParagraphStyle("h3", fontName="UI-SB", fontSize=11, leading=15, textColor=INK, spaceBefore=8, spaceAfter=3)
ss["small"] = ParagraphStyle("small", parent=ss["body"], fontSize=8.5, leading=11.5, textColor=MUTED)
ss["cap"] = ParagraphStyle("cap", parent=ss["small"], alignment=TA_CENTER, spaceBefore=3, spaceAfter=10)
ss["cell"] = ParagraphStyle("cell", fontName="UI", fontSize=9, leading=12, textColor=INK)
ss["cellb"] = ParagraphStyle("cellb", parent=ss["cell"], fontName="UI-SB")
ss["cellh"] = ParagraphStyle("cellh", parent=ss["cell"], fontName="UI-B", textColor=colors.white)
ss["mono"] = ParagraphStyle("mono", fontName="Mono", fontSize=7.6, leading=10, textColor=INK)

W = A4[0] - 4.4 * cm


def P(text, style="body"):
    return Paragraph(text, ss[style])


class Section(Paragraph):
    """Titre de section relevé pour le sommaire."""

    def __init__(self, key, text):
        super().__init__(text, ss["h1"])
        self.key = key


def section(num, key, title):
    return [PageBreak() if num > 1 else Spacer(0, 0), P(f"SECTION {num}", "kicker"), Section(key, title)]


def box(text, kind="tip", title=None):
    bg, bd = {"tip": (TIP_BG, TEAL), "warn": (WARN_BG, WARN_BD), "info": (INFO_BG, INFO_BD)}[kind]
    label = title or {"tip": "Conseil", "warn": "Attention", "info": "À savoir"}[kind]
    content = [Paragraph(f"<b>{label}</b>", ss["cellb"]), Spacer(1, 2)]
    for t in ([text] if isinstance(text, str) else text):
        content.append(Paragraph(t, ss["cell"]))
    t = Table([[content]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, bd),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return KeepTogether([Spacer(1, 4), t, Spacer(1, 8)])


def table(rows, widths, header=True):
    data = []
    for i, r in enumerate(rows):
        data.append([Paragraph(str(c), ss["cellh" if header and i == 0 else "cellb" if j == 0 else "cell"])
                     for j, c in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), TEAL_DARK))
    for i in range(1 if header else 0, len(rows)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), SOFT))
    t.setStyle(TableStyle(style))
    return t


def code(lines):
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
    t = Table([[Paragraph(esc(l) or "&nbsp;", ss["mono"])] for l in lines], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 0.3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0.3),
                           ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, -1), (-1, -1), 6)]))
    return KeepTogether(t)


def shot(name, caption, width=13.5 * cm):
    path = SHOTS / name
    w, h = PILImage.open(path).size
    img = Image(str(path), width=width, height=width * h / w)
    frame = Table([[img]], colWidths=[width + 2])
    frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 1),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 1), ("TOPPADDING", (0, 0), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return KeepTogether([frame, P(caption, "cap")])


def steps(items):
    out = []
    for i, t in enumerate(items, 1):
        num = Table([[Paragraph(f'<font color="white"><b>{i}</b></font>', ParagraphStyle(
            "n", fontName="UI-B", fontSize=9, leading=11, alignment=TA_CENTER))]], colWidths=[0.55 * cm],
            rowHeights=[0.55 * cm])
        num.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TEAL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                 ("ROUNDEDCORNERS", [8, 8, 8, 8]), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        row = Table([[num, Paragraph(t, ss["body"])]], colWidths=[0.85 * cm, W - 0.85 * cm])
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        out.append(row)
    return out


def bullets(items):
    return [Paragraph(t, ss["body"], bulletText="•") for t in items]


# ------------------------------------------------------------------ mise en page
def on_cover(c, doc):
    w, h = A4
    c.setFillColor(BLACK); c.rect(0, h - 11 * cm, w, 11 * cm, fill=1, stroke=0)
    c.setFillColor(TEAL); c.rect(0, h - 11 * cm, w, 0.18 * cm, fill=1, stroke=0)
    c.setFillColor(TEAL); c.setFont("UI-SB", 12); c.drawString(2.2 * cm, h - 3 * cm, "GUIDE D'UTILISATION")
    c.setFillColor(colors.white); c.setFont("UI-B", 36); c.drawString(2.2 * cm, h - 4.9 * cm, "SAV Service Tool")
    c.setFont("UI", 15)
    c.drawString(2.2 * cm, h - 6.1 * cm, "Maintenance des imprimantes jet d'encre Canon")
    c.drawString(2.2 * cm, h - 6.85 * cm, "Erreur 5B00, page calibrage, nettoyages — Windows 10 et 11")
    c.setFont("UI", 10); c.setFillColor(colors.HexColor("#C9D3E6"))
    c.drawString(2.2 * cm, h - 9.6 * cm, f"Version {VERSION}  •  Novembre 2026  •  Logiciel gratuit distribué par AKM12")
    c.setFillColor(MUTED); c.setFont("UI", 8.5)
    c.drawString(2.2 * cm, 1.9 * cm, "© 2026 AKM12 · akm12.com/logiciels/sav-service-tool")
    c.drawString(2.2 * cm, 1.45 * cm, "Logiciel indépendant, non édité ni approuvé par Canon. Canon et MAXIFY sont des marques de Canon Inc.")


def on_page(c, doc):
    w, h = A4
    c.setStrokeColor(LINE); c.setLineWidth(0.5)
    c.line(2.2 * cm, h - 1.5 * cm, w - 2.2 * cm, h - 1.5 * cm)
    c.setFont("UI", 8); c.setFillColor(MUTED)
    c.drawString(2.2 * cm, h - 1.25 * cm, f"SAV Service Tool {VERSION} — Guide d'utilisation")
    c.drawRightString(w - 2.2 * cm, h - 1.25 * cm, "akm12.com")
    c.drawRightString(w - 2.2 * cm, 1.2 * cm, f"{doc.page}")
    c.setFillColor(TEAL); c.rect(2.2 * cm, h - 1.52 * cm, 1.2 * cm, 0.06 * cm, fill=1, stroke=0)


class Doc(BaseDocTemplate):
    def __init__(self, path, pages):
        super().__init__(str(path), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2.1 * cm,
                         bottomMargin=1.9 * cm, title=f"SAV Service Tool {VERSION} — Guide d'utilisation", author="AKM12",
                         subject="Maintenance des imprimantes jet d'encre Canon")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        cover = Frame(self.leftMargin, self.bottomMargin + 1.5 * cm, self.width,
                      A4[1] - 13.5 * cm - self.bottomMargin, id="c")
        self.addPageTemplates([PageTemplate("cover", [cover], onPage=on_cover),
                               PageTemplate("main", [frame], onPage=on_page)])
        self.pages = pages

    def afterFlowable(self, flowable):
        if isinstance(flowable, Section):
            self.pages[flowable.key] = self.page


TOC = story.TOC

pages: dict[str, int] = {}
_self = sys.modules[__name__]
Doc(OUT, pages).build(story.build({}, _self))           # 1er passage : relève les pages des sections
Doc(OUT, pages).build(story.build(dict(pages), _self))  # 2e passage : sommaire avec les bons numéros
print("pages des sections :", pages)
