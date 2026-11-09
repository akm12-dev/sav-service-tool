"""SAV Service Tool - outil de maintenance pour imprimantes jet d'encre Canon.

Lancement :  python service_tool.py
"""
import json
import os
import sys
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

import threading
import queue

import webbrowser
import subprocess

import printer_io
import canon_reset
import canon_network
import canon_ivec

APP_NAME = "SAV Service Tool"
APP_VERSION = "2.0.1"
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
COMMANDS_FILE = os.path.join(HERE, "commands.json")

SERVICE_MODE_HELP = (
    "Passer l'imprimante en MODE SERVICE (séquence la plus courante) :\n\n"
    "1. Éteindre l'imprimante (câble USB branché).\n"
    "2. Maintenir STOP/RESET enfoncé.\n"
    "3. Maintenir aussi POWER.\n"
    "4. Tout en gardant POWER, relâcher STOP.\n"
    "5. Appuyer 5 fois sur STOP (selon modèle : 2 à 6 fois).\n"
    "6. Relâcher POWER et STOP en même temps.\n\n"
    "Le voyant clignote puis reste fixe (écran vide ou 'Idle' sur les MAXIFY).\n"
    "Windows peut détecter un nouveau périphérique : c'est normal."
)


class ServiceTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        # Icône de fenêtre : fournie dans l'exe (PyInstaller) ou dans assets\ en mode script
        base = getattr(sys, "_MEIPASS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
        try:
            self.iconbitmap(default=os.path.join(base, "sav.ico"))
            # Grande icône (barre des tâches, Alt+Tab)
            self._icon = tk.PhotoImage(file=os.path.join(base, "sav-256.png"))
            self.iconphoto(True, self._icon)
        except tk.TclError:
            pass
        self.geometry("1100x800")
        self.commands = self._load_commands()
        self._q = queue.Queue()
        self._build_ui()
        self._poll_ui()
        self.refresh_printers()
        self.log(f"{APP_NAME} {APP_VERSION} démarré.")
        try:
            canon_reset.self_test()
            self.log("Autotest chiffrement 5B00 : OK.")
        except canon_reset.ResetError as e:
            self.log(str(e))
        self.detect_usb()
        self._show_usb_firmware()
        self.find_network()

    # ------------------------------------------------------------ données
    def _load_commands(self):
        bundled = os.path.join(getattr(sys, "_MEIPASS", HERE), "commands.json")
        if not os.path.exists(COMMANDS_FILE) and os.path.exists(bundled):
            import shutil
            shutil.copyfile(bundled, COMMANDS_FILE)  # copie par défaut à côté de l'exe
        try:
            with open(COMMANDS_FILE, encoding="utf-8") as f:
                return json.load(f)["commands"]
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_NAME, f"Impossible de lire commands.json :\n{e}")
            return {}

    # ------------------------------------------------------------ thème
    C = {
        "bg": "#eef1f6", "card": "#ffffff", "border": "#dde3ec", "text": "#1c2433", "muted": "#6b7588",
        "nav": "#16213a", "nav_hover": "#22304f", "nav_active": "#2f6fed", "nav_text": "#c9d3e6",
        "accent": "#2f6fed", "accent_hover": "#245ad0", "danger": "#e8590c", "danger_hover": "#c94a07",
        "ok": "#1f9d55", "warn": "#d97706", "err": "#d64545",
        "log_bg": "#0f1626", "log_text": "#cfd8e8",
    }

    def _setup_style(self):
        C = self.C
        self.configure(bg=C["bg"])
        import tkinter.font as tkfont
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            tkfont.nametofont(name).configure(family="Segoe UI", size=10)
        self.option_add("*TCombobox*Listbox.font", "{Segoe UI} 10")
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=C["bg"], foreground=C["text"], font=("Segoe UI", 10),
                     bordercolor=C["border"], lightcolor=C["card"], darkcolor=C["border"])
        st.configure("Card.TFrame", background=C["card"])
        st.configure("Bg.TFrame", background=C["bg"])
        st.configure("Card.TLabel", background=C["card"], foreground=C["text"])
        st.configure("Muted.TLabel", background=C["card"], foreground=C["muted"], font=("Segoe UI", 9))
        st.configure("CardTitle.TLabel", background=C["card"], foreground=C["text"],
                     font=("Segoe UI Semibold", 12))
        st.configure("PageTitle.TLabel", background=C["bg"], foreground=C["text"], font=("Segoe UI Semibold", 17))
        st.configure("PageSub.TLabel", background=C["bg"], foreground=C["muted"], font=("Segoe UI", 10))
        st.configure("Card.TCheckbutton", background=C["card"], foreground=C["text"])
        st.map("Card.TCheckbutton", background=[("active", C["card"])])
        st.configure("Card.TRadiobutton", background=C["card"], foreground=C["text"])
        st.map("Card.TRadiobutton", background=[("active", C["card"])])
        st.configure("TCombobox", padding=5, arrowsize=14, fieldbackground=C["card"])
        st.map("TCombobox", fieldbackground=[("readonly", C["card"])],
               selectbackground=[("readonly", C["card"])], selectforeground=[("readonly", C["text"])])
        # Boutons
        st.configure("TButton", padding=(14, 7), relief="flat", background="#e6ebf3",
                     foreground=C["text"], borderwidth=0, focuscolor="")
        st.map("TButton", background=[("disabled", "#eef1f6"), ("active", "#d6dde9")],
               foreground=[("disabled", "#a0a8b8")])
        for name, bg, hov in (("Accent", C["accent"], C["accent_hover"]), ("Danger", C["danger"], C["danger_hover"])):
            st.configure(f"{name}.TButton", background=bg, foreground="white",
                         font=("Segoe UI Semibold", 10), padding=(18, 9))
            st.map(f"{name}.TButton", background=[("disabled", "#b9c2d3"), ("active", hov)],
                   foreground=[("disabled", "white")])
        st.configure("Tile.TButton", padding=(10, 16), font=("Segoe UI Semibold", 10),
                     background="#f3f6fb", anchor="center")
        st.map("Tile.TButton", background=[("active", "#e3eaf6")])
        st.configure("Treeview", rowheight=26, background=C["card"], fieldbackground=C["card"], borderwidth=0)
        st.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background="#f3f6fb", relief="flat")

    # ------------------------------------------------------------ interface
    def _build_ui(self):
        C = self.C
        self._setup_style()
        self.minsize(1040, 720)

        # Menu
        menu = tk.Menu(self)
        m_file = tk.Menu(menu, tearoff=False)
        m_file.add_command(label="Recharger commands.json", command=self.reload_commands)
        m_file.add_separator()
        m_file.add_command(label="Quitter", command=self.destroy)
        menu.add_cascade(label="Fichier", menu=m_file)
        m_help = tk.Menu(menu, tearoff=False)
        m_help.add_command(label="Mode service...", command=lambda: messagebox.showinfo("Mode service", SERVICE_MODE_HELP))
        m_help.add_command(label="À propos...", command=self.about)
        menu.add_cascade(label="?", menu=m_help)
        self.config(menu=menu)

        # ---- barre latérale
        side = tk.Frame(self, bg=C["nav"], width=228)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="SAV", bg=C["nav"], fg="white", font=("Segoe UI Black", 22)).pack(anchor="w", padx=22, pady=(22, 0))
        tk.Label(side, text="Service Tool", bg=C["nav"], fg=C["nav_text"],
                 font=("Segoe UI", 11)).pack(anchor="w", padx=22)
        tk.Frame(side, bg=C["nav_hover"], height=1).pack(fill="x", padx=18, pady=18)
        self._nav = {}
        self._pages = {}
        for key, icon, label in (("dash", "⌂", "Tableau de bord"), ("maint", "⎙", "Entretien"),
                                 ("reset", "⟲", "Erreur 5B00"), ("net", "⌘", "Réseau & firmware"),
                                 ("adv", "⚙", "Avancé")):
            b = tk.Label(side, text=f"  {icon}   {label}", anchor="w", bg=C["nav"], fg=C["nav_text"],
                         font=("Segoe UI", 11), padx=14, pady=10, cursor="hand2")
            b.pack(fill="x", padx=10, pady=2)
            b.bind("<Button-1>", lambda e, k=key: self.show_page(k))
            b.bind("<Enter>", lambda e, k=key: self._nav_hover(k, True))
            b.bind("<Leave>", lambda e, k=key: self._nav_hover(k, False))
            self._nav[key] = b
        tk.Label(side, text=f"Version {APP_VERSION}", bg=C["nav"], fg="#6e7a93",
                 font=("Segoe UI", 9)).pack(side="bottom", anchor="w", padx=22, pady=16)

        # ---- zone principale
        main = tk.Frame(self, bg=C["bg"])
        main.pack(side="left", fill="both", expand=True)

        # cartes d'état
        cards = tk.Frame(main, bg=C["bg"])
        cards.pack(fill="x", padx=24, pady=(20, 8))
        self.ip_var = tk.StringVar(value="—")
        self.fw_var = tk.StringVar(value="—")
        self.model_var = tk.StringVar(value="—")
        self.mode_var = tk.StringVar(value="—")
        self._mode_lbl = None
        for i, (title, var) in enumerate((("IMPRIMANTE USB", self.model_var), ("ADRESSE IP", self.ip_var),
                                          ("FIRMWARE", self.fw_var), ("MODE", self.mode_var))):
            card = self._card(cards, pad=(16, 12))
            card.master.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            cards.columnconfigure(i, weight=3 if i == 0 else 2, uniform="c")
            ttk.Label(card, text=title, style="Muted.TLabel").pack(anchor="w")
            lbl = tk.Label(card, textvariable=var, bg=C["card"], fg=C["text"], font=("Segoe UI Semibold", 14),
                           anchor="w")
            lbl.pack(anchor="w", fill="x", pady=(2, 0))
            if title == "MODE":
                self._mode_lbl = lbl

        # pages
        self._page_host = tk.Frame(main, bg=C["bg"])
        self._page_host.pack(fill="both", expand=True, padx=24)
        self._net = []
        self._usb = []
        self._build_dash_page()
        self._build_maint_page()
        self._build_reset_page()
        self._build_net_page()
        self._build_adv_page()

        # journal
        logwrap = tk.Frame(main, bg=C["bg"])
        logwrap.pack(fill="x", padx=24, pady=(8, 20))
        head = tk.Frame(logwrap, bg=C["log_bg"])
        head.pack(fill="x")
        tk.Label(head, text="  JOURNAL", bg=C["log_bg"], fg="#7f8db0", font=("Segoe UI Semibold", 9)).pack(
            side="left", pady=(8, 2), padx=6)
        self.log_txt = tk.Text(logwrap, height=8, state="disabled", font=("Consolas", 9), bg=C["log_bg"],
                               fg=C["log_text"], relief="flat", padx=12, pady=6, wrap="word",
                               insertbackground="white", selectbackground="#2f4a7a", borderwidth=0)
        self.log_txt.pack(fill="x")
        self.log_txt.tag_configure("ts", foreground="#5d6b8a")
        self.log_txt.tag_configure("ok", foreground="#4ade80")
        self.log_txt.tag_configure("err", foreground="#f87171")
        self.log_txt.tag_configure("warn", foreground="#fbbf24")
        self.log_txt.tag_configure("head", foreground="#93c5fd")

        self.show_page("dash")

    # ---- éléments réutilisables
    def _card(self, parent, pad=(18, 16)):
        """Carte blanche avec bordure fine ; renvoie le cadre intérieur."""
        outer = tk.Frame(parent, bg=self.C["border"])
        inner = ttk.Frame(outer, style="Card.TFrame", padding=pad)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        return inner

    def _page(self, key, title, subtitle):
        f = tk.Frame(self._page_host, bg=self.C["bg"])
        ttk.Label(f, text=title, style="PageTitle.TLabel").pack(anchor="w", pady=(8, 0))
        ttk.Label(f, text=subtitle, style="PageSub.TLabel").pack(anchor="w", pady=(0, 12))
        self._pages[key] = f
        return f

    def _section(self, parent, title, subtitle=None, **pack):
        card = self._card(parent)
        card.master.pack(fill="x", pady=(0, 12), **pack)
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(card, text=subtitle, style="Muted.TLabel", wraplength=700, justify="left").pack(
                anchor="w", pady=(2, 0))
        body = ttk.Frame(card, style="Card.TFrame")
        body.pack(fill="x", pady=(12, 0))
        return body

    def _btn(self, parent, key, style="TButton", text=None, width=16, **params):
        label = text or self.commands.get(key, {}).get("label", key).split(" (")[0].split("  ->")[0]
        return ttk.Button(parent, text=label, width=width, style=style, command=lambda: self.run(key, **params))

    def _nav_hover(self, key, on):
        if key != getattr(self, "_current_page", None):
            self._nav[key].configure(bg=self.C["nav_hover"] if on else self.C["nav"])

    def show_page(self, key):
        for k, p in self._pages.items():
            p.pack_forget()
            self._nav[k].configure(bg=self.C["nav"], fg=self.C["nav_text"])
        self._pages[key].pack(fill="both", expand=True)
        self._nav[key].configure(bg=self.C["nav_active"], fg="white")
        self._current_page = key

    # ---- pages
    def _build_dash_page(self):
        p = self._page("dash", "Tableau de bord", "Actions rapides sur l'imprimante connectée.")
        grid = tk.Frame(p, bg=self.C["bg"])
        grid.pack(fill="x")
        tiles = (("Page de test", lambda: self.run("test_print")),
                 ("Page calibrage", lambda: self.run("nozzle_check")),
                 ("Nettoyage", lambda: self.run("cleaning")),
                 ("Erreur 5B00", lambda: self.show_page("reset")),
                 ("Interface web", self.open_web),
                 ("Actualiser", self.refresh_all))
        for i, (txt, cmd) in enumerate(tiles):
            b = ttk.Button(grid, text=txt, style="Tile.TButton", command=cmd)
            b.grid(row=i // 3, column=i % 3, sticky="nsew", padx=(0 if i % 3 == 0 else 10, 0), pady=(0, 10))
            grid.columnconfigure(i % 3, weight=1, uniform="t")
        info = self._section(p, "Conseil", None)
        ttk.Label(info, style="Card.TLabel", wraplength=720, justify="left",
                  text="Avant une remise à zéro 5B00, remplacez ou nettoyez les tampons d'encre usagée. "
                       "Cliquez sur « Actualiser » en mode normal avant de passer en mode service, "
                       "pour que le logiciel mémorise le modèle.").pack(anchor="w")

    def _build_maint_page(self):
        p = self._page("maint", "Entretien", "Impressions de test et nettoyage des têtes d'impression.")
        s = self._section(p, "Impression",
                          "La page de test passe par le pilote Windows ; la page calibrage est imprimée "
                          "directement par l'imprimante.")
        row = ttk.Frame(s, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="File d'impression :", style="Card.TLabel").pack(side="left")
        self.printer_var = tk.StringVar()
        self.printer_cb = ttk.Combobox(row, textvariable=self.printer_var, state="readonly", width=40)
        self.printer_cb.pack(side="left", padx=8)
        self.only_canon = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text="Canon USB uniquement", style="Card.TCheckbutton", variable=self.only_canon,
                        command=self.refresh_printers).pack(side="left", padx=6)
        row = ttk.Frame(s, style="Card.TFrame")
        row.pack(fill="x", pady=(12, 0))
        self._btn(row, "test_print", "Accent.TButton", "Page de test", width=18).pack(side="left")
        self._btn(row, "nozzle_check", "Accent.TButton", "Page calibrage", width=18).pack(side="left", padx=10)

        s = self._section(p, "Nettoyage",
                          "Le nettoyage en profondeur consomme beaucoup d'encre et remplit les tampons "
                          "d'encre usagée : à utiliser seulement si un nettoyage normal ne suffit pas.")
        row = ttk.Frame(s, style="Card.TFrame")
        row.pack(fill="x")
        for key, txt in (("cleaning", "Nettoyage"), ("cleaning_bk", "Nettoyage noir"),
                         ("cleaning_cl", "Nettoyage couleur")):
            self._btn(row, key, text=txt, width=17).pack(side="left", padx=(0, 10))
        self._btn(row, "deep_cleaning", "Danger.TButton", "Nettoyage profond", width=17).pack(side="left")

    def _build_reset_page(self):
        C = self.C
        p = self._page("reset", "Erreur 5B00 — compteur d'encre usagée",
                       "Remise à zéro de l'absorbeur d'encre (erreurs 5B00 / 5B01 / 1700).")
        cols = tk.Frame(p, bg=C["bg"])
        cols.pack(fill="both", expand=True)
        # La colonne « Marche à suivre » est placée en premier pour garder sa largeur
        right = tk.Frame(cols, bg=C["bg"], width=300)
        right.pack(side="right", fill="y", padx=(12, 0))
        left = tk.Frame(cols, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True)

        s = self._section(left, "Imprimante")
        row = ttk.Frame(s, style="Card.TFrame")
        row.pack(fill="x")
        self.usb_cb = ttk.Combobox(row, state="readonly", width=34)
        self.usb_cb.pack(side="left")
        self.usb_cb.bind("<<ComboboxSelected>>", lambda e: self._show_profile())
        ttk.Button(row, text="Détecter", command=self.detect_usb).pack(side="left", padx=8)
        self.profile_lbl = tk.Label(s, text="", bg=C["card"], font=("Segoe UI Semibold", 10), anchor="w")
        self.profile_lbl.pack(anchor="w", pady=(10, 0))

        s = self._section(left, "Remise à zéro")
        row = ttk.Frame(s, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="Absorbeur :", style="Card.TLabel").pack(side="left")
        self.clear_abs = ttk.Combobox(row, state="readonly", width=10, values=["Main", "Platen"])
        self.clear_abs.set("Main")
        self.clear_abs.pack(side="left", padx=8)
        self.force_var = tk.BooleanVar()
        ttk.Checkbutton(s, text="Forcer le protocole sur un modèle non validé", style="Card.TCheckbutton",
                        variable=self.force_var).pack(anchor="w", pady=(10, 0))
        self.clear_btn = ttk.Button(s, text="Remettre le compteur à zéro", style="Danger.TButton",
                                    command=self.clear_ink_counter)
        self.clear_btn.pack(anchor="w", pady=(14, 0))

        steps = self._card(right, pad=(16, 14))
        steps.master.pack(fill="both", expand=True)
        ttk.Label(steps, text="Marche à suivre", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))
        for i, t in enumerate((
                "Remplacer / nettoyer les tampons d'encre usagée.",
                "Cliquer sur « Détecter » (mode normal).",
                "Éteindre. Maintenir STOP (orange), maintenir ON, relâcher STOP, 5× STOP, relâcher ON.",
                "« Détecter » : le mode doit indiquer « Service ».",
                "Cliquer sur « Remettre le compteur à zéro ».",
                "Éteindre avec le bouton ON (ne pas débrancher), puis rallumer."), 1):
            r = ttk.Frame(steps, style="Card.TFrame")
            r.pack(fill="x", pady=3)
            tk.Label(r, text=str(i), bg=C["accent"], fg="white", font=("Segoe UI Semibold", 9),
                     width=2).pack(side="left", anchor="n", pady=2)
            ttk.Label(r, text=t, style="Card.TLabel", wraplength=225, justify="left").pack(
                side="left", padx=8, anchor="w")

    def _build_net_page(self):
        p = self._page("net", "Réseau & firmware", "Imprimantes Canon trouvées sur le réseau local.")
        s = self._section(p, "Imprimantes sur le réseau")
        self.net_tree = ttk.Treeview(s, columns=("ip", "model", "fw", "mac"), show="headings", height=4)
        for c, t, w in (("ip", "Adresse IP", 130), ("model", "Modèle", 230), ("fw", "Firmware", 90),
                        ("mac", "Adresse MAC", 160)):
            self.net_tree.heading(c, text=t, anchor="w")
            self.net_tree.column(c, width=w, anchor="w")
        self.net_tree.pack(fill="x")
        self.net_tree.bind("<<TreeviewSelect>>", self._net_selected)
        row = ttk.Frame(s, style="Card.TFrame")
        row.pack(fill="x", pady=(12, 0))
        ttk.Button(row, text="Rechercher", style="Accent.TButton", command=self.find_network).pack(side="left")
        ttk.Button(row, text="Interface web", command=self.open_web).pack(side="left", padx=10)
        s = self._section(p, "Firmware",
                          "⚠ La remise à zéro 5B00 a été validée sur le firmware 1.130. Une mise à jour peut "
                          "la bloquer définitivement : ne mettez à jour qu'en cas de besoin.")
        ttk.Button(s, text="Mise à jour du firmware…", command=self.firmware_update).pack(anchor="w")

    def _build_adv_page(self):
        p = self._page("adv", "Avancé", "Fonctions de l'outil de service Canon (la plupart non disponibles pour l'instant).")
        canvas = tk.Canvas(p, bg=self.C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(p, orient="vertical", command=canvas.yview)
        root = tk.Frame(canvas, bg=self.C["bg"])
        root.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=root, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-int(e.delta / 120), "units")
                        if self._current_page == "adv" else None)
        self._build_main_tab(root)

    def _build_main_tab(self, root):
        # Print / Operation
        f = self._section(root, "EEPROM et opérations")
        for k in ("eeprom_print", "integration", "eeprom_save", "log_save", "panel_check"):
            self._btn(f, k, width=14).pack(side="left", padx=(0, 8))
        self.auto_cleaning = tk.BooleanVar()

        # Set Destination
        f = self._section(root, "Set Destination")
        ttk.Label(f, text="Region :", width=10, style="Card.TLabel").pack(side="left")
        self.region = ttk.Combobox(f, state="readonly", width=12,
                                   values=["JPN", "USA", "EUR", "AUS", "ASA", "CHN", "KOR", "TWN", "LTN"])
        self.region.set("EUR")
        self.region.pack(side="left")
        ttk.Button(f, text="Set", width=8,
                   command=lambda: self.run("set_destination", region=self.region.get())).pack(side="right")

        # Ink Absorber Counter
        f = self._section(root, "Ink Absorber Counter")
        ttk.Label(f, text="Absorber :", width=10, style="Card.TLabel").pack(side="left")
        self.set_abs = ttk.Combobox(f, state="readonly", width=12, values=["Main", "Platen"])
        self.set_abs.set("Main")
        self.set_abs.pack(side="left")
        ttk.Label(f, text="Counter Value(%) :", style="Card.TLabel").pack(side="left", padx=(16, 4))
        self.abs_value = ttk.Combobox(f, state="readonly", width=6, values=[str(v) for v in range(0, 101, 10)])
        self.abs_value.set("0")
        self.abs_value.pack(side="left")
        ttk.Button(f, text="Set", width=8,
                   command=lambda: self.run("set_absorber_counter", absorber=self.set_abs.get(),
                                            value=self.abs_value.get(), confirm=True)).pack(side="right")

        # Pump Counter
        f = self._section(root, "Pump Counter")
        ttk.Label(f, text="Value :", width=10, style="Card.TLabel").pack(side="left")
        self.pump_value = ttk.Combobox(f, state="readonly", width=12, values=["0", "1", "2", "3"])
        self.pump_value.set("0")
        self.pump_value.pack(side="left")
        ttk.Button(f, text="Set", width=8,
                   command=lambda: self.run("pump_counter", value=self.pump_value.get(), confirm=True)).pack(side="right")

        # New Function
        f = self._section(root, "New Function")
        grid = [("write_sn", "system_cleaning", "calibration"),
                ("user_cleaning_off", "error_status")]
        for r, keys in enumerate(grid):
            for c, k in enumerate(keys):
                self._btn(f, k).grid(row=r, column=c, padx=(0, 8), pady=(0, 8), sticky="w")

        # Paper Feed Endurance
        f = self._section(root, "Paper Feed Endurance")
        self.paper = tk.StringVar(value="A4")
        self.tray = tk.StringVar(value="RearTray")
        self.copies = tk.StringVar(value="10")
        for i, p in enumerate(("A4", "Duplex", "Hagaki", "A3")):
            ttk.Radiobutton(f, text=p, variable=self.paper, value=p, style="Card.TRadiobutton").grid(
                row=i, column=0, sticky="w", padx=6)
        for i, t in enumerate(("RearTray", "Cassette", "Cassette2")):
            ttk.Radiobutton(f, text=t, variable=self.tray, value=t, style="Card.TRadiobutton").grid(
                row=i, column=1, sticky="w", padx=6)
        for i, n in enumerate(("10", "20", "50", "100")):
            ttk.Radiobutton(f, text=f"{n} copy", variable=self.copies, value=n, style="Card.TRadiobutton").grid(
                row=i, column=2, sticky="w", padx=6)
        ttk.Button(f, text="Endurance", width=16,
                   command=lambda: self.run("endurance", paper=self.paper.get(), tray=self.tray.get(),
                                            copies=self.copies.get())).grid(row=1, column=3, rowspan=2, padx=30)

        # Set Service Transportation Mode
        f = self._section(root, "Set Service Transportation Mode")
        ttk.Label(f, text="Flag :", width=10, style="Card.TLabel").pack(side="left")
        self.flag = ttk.Combobox(f, state="readonly", width=12, values=["ON", "OFF"])
        self.flag.set("ON")
        self.flag.pack(side="left")
        ttk.Button(f, text="Set", width=8,
                   command=lambda: self.run("transport_mode", flag=self.flag.get(), confirm=True)).pack(side="right")

    # ------------------------------------------------------------ fils d'exécution
    def _ui(self, fn, *args):
        """Planifie fn(*args) dans le fil de l'interface (sûr depuis un autre fil)."""
        self._q.put((fn, args))

    def _poll_ui(self):
        try:
            while True:
                fn, args = self._q.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.after(100, self._poll_ui)

    # ------------------------------------------------------------ actions
    def log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        low = msg.lower()
        if "✔" in msg or "ok." in low or "succès" in low:
            tag = "ok"
        elif "échec" in low or "erreur" in low or "impossible" in low or "✖" in msg:
            tag = "err"
        elif "attention" in low or "aucune" in low or "non trouvée" in low:
            tag = "warn"
        elif msg.startswith("---") or "démarré" in low:
            tag = "head"
        else:
            tag = None
        self.log_txt.configure(state="normal")
        self.log_txt.insert("end", f"{ts}  ", "ts")
        self.log_txt.insert("end", f"{msg}\n", tag)
        self.log_txt.see("end")
        self.log_txt.configure(state="disabled")
        try:
            with open(os.path.join(HERE, "service_tool.log"), "a", encoding="utf-8") as f:
                f.write(f"{datetime.date.today()} [{ts}] {msg}\n")
        except OSError:
            pass

    def refresh_printers(self):
        try:
            printers = printer_io.list_printers()
        except printer_io.PrinterError as e:
            self.log(str(e))
            printers = []
        if self.only_canon.get():
            printers = [p for p in printers
                        if "canon" in (p["name"] + p["driver"]).lower() and p["port"].upper().startswith("USB")
                        and "FAX" not in (p["name"] + p["driver"]).upper()]  # jamais la file fax
        self._printers = printers
        self.printer_cb["values"] = [f'{p["name"]}  [{p["port"]}]' for p in printers]
        if printers:
            self.printer_cb.current(0)
        else:
            self.printer_var.set("")
        self.log(f"{len(printers)} imprimante(s) détectée(s).")

    def reload_commands(self):
        self.commands = self._load_commands()
        self.log("commands.json rechargé.")

    def _selected_printer(self):
        i = self.printer_cb.current()
        return self._printers[i]["name"] if 0 <= i < len(self._printers) else None

    def _build_payload(self, cmd, params):
        payload = cmd.get("payload", "")
        if params:
            payload = payload.format(**params)
        if cmd.get("format") == "hex":
            return bytes.fromhex(payload.replace(" ", "").replace("\n", ""))
        return payload.encode("ascii")

    # ------------------------------------------------------------ impressions de test / nettoyage
    def _usb_send(self, label, data):
        d = self._current_usb()
        if not d:
            messagebox.showerror(APP_NAME, "Aucune imprimante Canon USB détectée (bouton « Détecter »).")
            return
        self.log(f"{label} : envoi à {d.model or '?'} (USB)…")

        def worker():
            try:
                with canon_reset.UsbPrinter(d.path) as u:
                    n = u.write(data)
                if any(m in (d.model or "").upper() for m in canon_ivec.VALIDATED_MODELS):
                    self._ui(self.log, f"{label} : ✔ commande envoyée avec succès, l'imprimante l'exécute.")
                else:
                    self._ui(self.log, f"{label} : ✔ commande envoyée ({n} octets). Modèle pas encore testé : "
                                       "s'il ne réagit pas, c'est qu'il ne prend pas en charge cette commande.")
            except Exception as e:  # noqa: BLE001
                self._ui(self.log, f"{label} : ÉCHEC - {e}")
                self._ui(messagebox.showerror, APP_NAME, f"{label} :\n{e}")

        threading.Thread(target=worker, daemon=True).start()

    def windows_test_page(self):
        printer = self._selected_printer()
        if not printer:
            messagebox.showerror(APP_NAME, "Aucune imprimante sélectionnée en haut de la fenêtre.")
            return
        subprocess.Popen(["rundll32", "printui.dll,PrintUIEntry", "/k", "/n", printer])
        self.log(f"Page de test Windows envoyée à {printer}.")

    def run(self, key, confirm=False, **params):
        if key == "test_print":
            self.windows_test_page()
            return
        if key in canon_ivec.ACTIONS:
            label, build = canon_ivec.ACTIONS[key]
            if key == "deep_cleaning" and not messagebox.askyesno(APP_NAME,
                    "Le nettoyage en profondeur consomme beaucoup d'encre "
                    "et envoie de l'encre dans les tampons d'encre usagée.\n\nContinuer ?"):
                return
            self._usb_send(label, build())
            return
        cmd = self.commands.get(key)
        if not cmd:
            self.log(f"Commande inconnue : {key}")
            return
        label = cmd["label"].format(**params) if params else cmd["label"]

        if cmd.get("status") == "missing" or not cmd.get("payload"):
            self.log(f"{label} : trame non définie dans commands.json.")
            messagebox.showwarning(APP_NAME,
                f"« {label} »\n\nAucune trame n'est définie pour cette fonction.\n"
                "Ajoutez-la dans commands.json (champ 'payload'), puis Fichier > Recharger.")
            return
        printer = self._selected_printer()
        if not printer:
            messagebox.showerror(APP_NAME, "Aucune imprimante sélectionnée.")
            return
        if cmd.get("status") == "unverified":
            self.log(f"Attention : « {label} » n'a pas encore été validée sur ce modèle.")
        if confirm and not messagebox.askyesno(APP_NAME,
                f"Exécuter « {label} » sur\n{printer} ?\n\nL'imprimante doit être en mode service."):
            return
        try:
            data = self._build_payload(cmd, params)
            n = printer_io.send_raw(printer, data, doc_name=f"{APP_NAME} - {key}")
            self.log(f"{label} : {n} octet(s) envoyés à {printer}.")
        except (ValueError, KeyError) as e:
            self.log(f"{label} : trame invalide ({e}).")
        except printer_io.PrinterError as e:
            self.log(f"{label} : {e}")
            messagebox.showerror(APP_NAME, str(e))

    # ------------------------------------------------------------ RAZ 5B00
    def detect_usb(self):
        try:
            self._usb = [d for d in canon_reset.detect() if "FAX" not in d.model.upper()]
        except canon_reset.ResetError as e:
            self.log(str(e))
            self._usb = []
        self.usb_cb["values"] = [f"{d.model or '(modèle inconnu)'}  [PID {d.pid}]" for d in self._usb]
        if self._usb:
            self.usb_cb.current(0)
        else:
            self.usb_cb.set("")
        last_file = os.path.join(HERE, "last_model.txt")
        for d in self._usb:
            self.log(f"USB : {d.model or '?'} PID {d.pid} - {d.device_id[:120]}")
            if d.profile:  # mode normal : on mémorise le modèle
                try:
                    with open(last_file, "w", encoding="utf-8") as f:
                        f.write(d.model)
                except OSError:
                    pass
            elif d.model.upper() in ("DEVICE", ""):  # mode service : le modèle n'est plus annoncé
                try:
                    with open(last_file, encoding="utf-8") as f:
                        last = f.read().strip()
                except OSError:
                    last = ""
                prof = canon_reset.match_profile(last)
                if prof:
                    d.model = f"{last} (mode service)"
                    d.profile = prof
                    self.log(f"Mode service détecté - modèle mémorisé : {last}.")
        self.usb_cb["values"] = [f"{d.model or '(modèle inconnu)'}  [PID {d.pid}]" for d in self._usb]
        if self._usb:
            self.usb_cb.current(0)
        if not self._usb:
            self.log("Aucune imprimante Canon USB détectée.")
        self._show_profile()

    def _current_usb(self):
        i = self.usb_cb.current()
        return self._usb[i] if 0 <= i < len(self._usb) else None

    def _show_profile(self):
        C = self.C
        d = self._current_usb()
        if not d:
            self.profile_lbl.config(text="Aucune imprimante Canon USB détectée.", fg=C["muted"])
            self.model_var.set("Non connectée")
            self.mode_var.set("—")
            self._mode_lbl.config(fg=C["muted"])
            return
        service = "(mode service)" in d.model or d.pid.lower() == "12fe"
        self.model_var.set(d.model.replace(" (mode service)", "") or "Inconnu")
        self.mode_var.set("Service" if service else "Normal")
        self._mode_lbl.config(fg=C["warn"] if service else C["ok"])
        if d.profile:
            self.profile_lbl.config(text="✔  Modèle pris en charge pour la remise à zéro", fg=C["ok"])
        else:
            self.profile_lbl.config(text="✖  Modèle non validé (option « Forcer » nécessaire)", fg=C["err"])

    def refresh_all(self):
        self.refresh_printers()
        self.detect_usb()
        self._show_usb_firmware()
        self.find_network()

    def clear_ink_counter(self):
        d = self._current_usb()
        if not d:
            messagebox.showerror(APP_NAME, "Cliquez d'abord sur « Détecter » (imprimante en mode service).")
            return
        absorber = self.clear_abs.get()
        profile = d.profile
        if not profile:
            if not self.force_var.get():
                messagebox.showwarning(APP_NAME,
                    f"Le modèle « {d.model or 'inconnu'} » n'a pas de profil validé.\n\n"
                    "Si l'imprimante est en mode service, son nom peut ne plus apparaître : "
                    "cochez « Forcer » pour utiliser le protocole G6000.\n\n"
                    "Sur un modèle non validé, le résultat n'est pas garanti.")
                return
            profile = "G6000"
        if profile == "G6000" and absorber != "Main" and d.profile:
            messagebox.showwarning(APP_NAME, "La série G6000 n'a qu'un absorbeur : « Main ».")
            return
        msg = (f"Remise à zéro du compteur « {absorber} »\nImprimante : {d.model or '?'} (PID {d.pid})\n"
               f"Protocole : {profile}{'  (FORCÉ - non validé sur ce modèle)' if not d.profile else ''}\n\n"
               "✔ Les tampons d'encre usagée ont été remplacés ou nettoyés ?\n"
               "✔ L'imprimante est en MODE SERVICE ?\n\nContinuer ?")
        if not messagebox.askyesno(APP_NAME, msg, icon="warning"):
            return
        self.clear_btn.config(state="disabled")
        self.log(f"--- RAZ absorbeur {absorber} ({profile}) ---")

        def worker():
            try:
                canon_reset.reset_absorber(d.path, profile, absorber, force=not d.profile,
                                           log=lambda m: self._ui(self.log, m))
                self._ui(lambda: messagebox.showinfo(APP_NAME,
                    "Commandes envoyées.\n\n" + canon_reset.COMMIT_INSTRUCTION +
                    "\n\nSi l'erreur 5B00 réapparaît au redémarrage, ce modèle n'accepte pas ce protocole."))
            except Exception as e:  # noqa: BLE001
                self._ui(self.log, f"ÉCHEC : {e}")
                self._ui(messagebox.showerror, APP_NAME, str(e))
            finally:
                self._ui(lambda: self.clear_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------ réseau / firmware
    def _usb_model(self):
        d = self._current_usb()
        return d.model.replace(" (mode service)", "") if d else ""

    def find_network(self):
        self.ip_var.set("recherche…")
        self.log("Recherche des imprimantes Canon sur le réseau…")

        def worker():
            try:
                found = canon_network.discover()
            except OSError as e:
                found = []
                self._ui(self.log, f"Recherche réseau impossible : {e}")
            self._ui(self._show_network, found)

        threading.Thread(target=worker, daemon=True).start()

    def _show_network(self, found):
        self._net = found
        self.net_tree.delete(*self.net_tree.get_children())
        for n in found:
            self.log(f"Réseau : {n.ip}  {n.model or '?'}  firmware {n.firmware or '?'}  MAC {n.mac or '?'}")
            self.net_tree.insert("", "end", iid=n.ip, values=(n.ip, n.model or "?", n.firmware or "?", n.mac or "?"))
        model = self._usb_model()
        match = [n for n in found if model and n.model == model] or found
        if match:
            n = match[0]
            self.ip_var.set(n.ip)
            self.fw_var.set(n.firmware or self.fw_var.get())
            if len(match) > 1:
                self.log(f"Plusieurs imprimantes {model} sur le réseau : affichée {n.ip}.")
        else:
            self.ip_var.set("non trouvée")
            self.log("Aucune imprimante Canon trouvée sur le réseau (même réseau que ce PC ?).")

    def _net_selected(self, _e=None):
        sel = self.net_tree.selection()
        if sel:
            n = next((x for x in self._net if x.ip == sel[0]), None)
            if n:
                self.ip_var.set(n.ip)
                self.fw_var.set(n.firmware or "—")

    def _show_usb_firmware(self):
        d = self._current_usb()
        if d:
            for part in d.device_id.split(";"):
                if part.startswith("VER:"):
                    self.fw_var.set(part[4:])

    def open_web(self):
        ip = self.ip_var.get()
        if not ip or not ip[0].isdigit():
            messagebox.showinfo(APP_NAME, "Cliquez d'abord sur « Rechercher sur le réseau ».")
            return
        webbrowser.open(f"http://{ip}/")
        self.log(f"Interface web ouverte : http://{ip}/")

    def firmware_update(self):
        ip = self.ip_var.get()
        if not ip or not ip[0].isdigit():
            messagebox.showinfo(APP_NAME, "Cliquez d'abord sur « Rechercher sur le réseau » "
                                          "(l'imprimante doit être connectée à Internet).")
            return
        fw = self.fw_var.get()
        if not messagebox.askyesno(APP_NAME,
                f"Firmware actuel : {fw}\n\n"
                "La mise à jour est faite par l'imprimante elle-même, depuis les serveurs Canon "
                "(procédure officielle). L'interface web de l'imprimante va s'ouvrir :\n"
                "  → menu « Paramètres du périphérique / Device settings »\n"
                "  → « Mise à jour du firmware / Firmware update »\n"
                "(sur l'imprimante : Configuration → Paramètres du périphérique → Mise à jour du firmware)\n\n"
                "⚠ ATTENTION : la remise à zéro 5B00 de ce logiciel a été validée sur le firmware 1.130. "
                "Une version plus récente peut la bloquer, sans retour en arrière possible.\n"
                "Ne coupez jamais le courant pendant la mise à jour.\n\nOuvrir l'interface web ?",
                icon="warning"):
            return
        self.log(f"Mise à jour firmware demandée (firmware actuel {fw}).")
        self.open_web()

    def about(self):
        messagebox.showinfo("À propos", f"{APP_NAME}\nVersion {APP_VERSION}\n\n"
                            "Logiciel gratuit développé et distribué par AKM12 — Advanced Knowledge & Maintenance.\n"
                            "https://akm12.com/logiciels/sav-service-tool\n\n"
                            "Logiciel indépendant, non édité par Canon. Licences tierces : THIRD_PARTY_NOTICES.txt")


if __name__ == "__main__":
    ServiceTool().mainloop()
