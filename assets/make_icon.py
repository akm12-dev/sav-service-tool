"""Dessine l'icône de SAV Service Tool (sav.ico + sav.png) aux couleurs de l'application.

Carré bleu nuit arrondi, imprimante blanche avec sa feuille bleue, pastille orange avec flèche de remise à zéro.
Usage : py make_icon.py   (écrit sav.ico et sav-256.png à côté de ce script)
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

NAV = (22, 33, 58)          # #16213a, barre latérale
BLUE = (47, 111, 237)       # #2f6fed, accent
ORANGE = (232, 89, 12)      # #e8590c, bouton de remise à zéro
WHITE = (255, 255, 255)
S = 1024                    # dessin en grand, réduit ensuite (bords lisses)


def draw() -> Image.Image:
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((32, 32, S - 32, S - 32), radius=210, fill=NAV)

    # Feuille qui sort de l'imprimante (bleue) et bac papier
    d.rounded_rectangle((300, 170, 680, 420), radius=28, fill=BLUE)
    # Corps de l'imprimante
    d.rounded_rectangle((170, 360, 810, 700), radius=70, fill=WHITE)
    # Fente de sortie
    d.rounded_rectangle((300, 600, 680, 650), radius=20, fill=NAV)
    # Voyant
    d.ellipse((640, 420, 700, 480), fill=BLUE)

    # Pastille orange avec flèche circulaire (remise à zéro)
    cx, cy, r = 735, 735, 200
    d.ellipse((cx - r - 26, cy - r - 26, cx + r + 26, cy + r + 26), fill=NAV)   # liseré de séparation
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ORANGE)
    ar, w = 108, 42
    d.arc((cx - ar, cy - ar, cx + ar, cy + ar), start=-60, end=230, fill=WHITE, width=w)
    # Pointe de flèche au bout de l'arc (angle -60°)
    a = math.radians(-60)
    tip_x, tip_y = cx + ar * math.cos(a), cy + ar * math.sin(a)
    size = 70
    d.polygon([(tip_x + size * 0.95, tip_y - size * 0.05),
               (tip_x - size * 0.55, tip_y - size * 0.75),
               (tip_x - size * 0.35, tip_y + size * 0.85)], fill=WHITE)
    return im


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    big = draw()
    big.resize((256, 256), Image.LANCZOS).save(here / "sav-256.png")
    big.resize((256, 256), Image.LANCZOS).save(
        here / "sav.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    # Planche de contrôle : l'icône aux tailles courantes
    sheet = Image.new("RGBA", (16 + 24 + 32 + 48 + 64 + 128 + 256 + 8 * 10, 266), (240, 242, 245, 255))
    x = 10
    for s in (16, 24, 32, 48, 64, 128, 256):
        sheet.alpha_composite(big.resize((s, s), Image.LANCZOS), (x, 266 - s - 5))
        x += s + 10
    sheet.save(here / "apercu-icone.png")
    print("ok")
