"""Captures du guide SAV Service Tool, avec une imprimante de démonstration.

Rien n'est envoyé à une imprimante : détection USB, recherche réseau et files d'impression sont simulées,
et toutes les fonctions qui écrivent (remise à zéro, nettoyages, impressions) lèvent une exception.

Usage : py shots.py <dossier_de_sortie>
"""
import ctypes
import os
import shutil
import sys
import tempfile
from pathlib import Path

OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# Fichiers d'exécution (journal, last_model.txt) écrits dans un dossier temporaire, pas dans le projet
RUN = Path(tempfile.mkdtemp(prefix="savst-guide-"))
shutil.copy(ROOT / "commands.json", RUN / "commands.json")
sys.argv[0] = str(RUN / "service_tool.py")
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import canon_network  # noqa: E402
import canon_reset  # noqa: E402
import printer_io  # noqa: E402

MODE = {"service": False}
DEMO_ID = "MFG:Canon;CMD:BJL,BJRaster3,BSCCe,NCCe,IVEC,IVECPLI;SOJ:TXT01;MDL:MB2100 series;CLS:PRINTER;VER:1.130;"


def fake_detect():
    if MODE["service"]:
        return [canon_reset.Detected("demo", "04a9", "12fe", "MFG:Canon;MDL:Device;", "MB2100 series (mode service)",
                                     "G6000")]
    return [canon_reset.Detected("demo", "04a9", "1793", DEMO_ID, "MB2100 series", "G6000")]


def refuse(*a, **k):
    raise RuntimeError("Désactivé pendant les captures du guide")


canon_reset.detect = fake_detect
canon_reset.reset_absorber = refuse
canon_reset.UsbPrinter.write = refuse
canon_network.discover = lambda *a, **k: [
    canon_network.NetPrinter("192.168.1.50", "00:00:5e:00:53:2a", DEMO_ID),
    canon_network.NetPrinter("192.168.1.61", "00:00:5e:00:53:3c", "MFG:Canon;MDL:G6000 series;VER:1.040;"),
]
printer_io.list_printers = lambda: [
    {"name": "Canon MB2100 series", "port": "USB001", "driver": "Canon MB2100 series"},
    {"name": "Canon MB2100 series FAX", "port": "USB004", "driver": "Canon MB2100 series FAX"},
]
printer_io.send_raw = refuse

from PIL import ImageGrab  # noqa: E402
import service_tool  # noqa: E402

service_tool.subprocess.Popen = refuse
for name in ("showinfo", "showwarning", "showerror"):
    setattr(service_tool.messagebox, name, lambda *a, **k: None)
service_tool.messagebox.askyesno = lambda *a, **k: False

app = service_tool.ServiceTool()
app.geometry("1100x800+10+10")
app.attributes("-topmost", True)

plan = [("dash", "1_tableau_de_bord", False), ("maint", "2_entretien", False), ("reset", "3_5b00_normal", False),
        ("reset", "4_5b00_service", True), ("net", "5_reseau", False), ("adv", "6_avance", False)]


def step(i=0):
    if i >= len(plan):
        app.destroy()
        return
    page, name, service = plan[i]
    if service != MODE["service"]:
        MODE["service"] = service
        app.detect_usb()
    app.show_page(page)

    def shot():
        app.update()
        x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
        ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(OUT / f"{name}.png")
        print("capture", name)
        step(i + 1)
    app.after(800, shot)


app.after(3500, step)            # laisse la recherche réseau (simulée) se terminer
app.mainloop()
shutil.rmtree(RUN, ignore_errors=True)
