"""Commandes de maintenance Canon « IVEC » (XML) : vérification des buses, nettoyages.

Format repris de canon-ij-maint (MIT, Taktek et Nizar Mahmoud) :
https://github.com/taktekhq/canon-ij-maint - octets identiques à ceux du filtre
Canon cmdtocanonij3. Testé par ses auteurs sur PIXMA G3010 ; les imprimantes qui
annoncent « IVEC » dans leur identifiant (CMD:...IVEC) devraient l'accepter.
Une commande non comprise est simplement ignorée par l'imprimante.
"""
_NS = 'xmlns:ivec="http://www.canon.com/ns/cmd/2008/07/common/"'
JOB_ID = "00000001"


def _start_job(job=JOB_ID):
    return ('<?xml version="1.0" encoding="utf-8" ?>'
            f'<cmd {_NS}><ivec:contents><ivec:operation>StartJob</ivec:operation>'
            '<ivec:param_set servicetype="maintenance">'
            f'<ivec:jobID>{job}</ivec:jobID><ivec:bidi>0</ivec:bidi>'
            '<ivec:jobname/><ivec:username/><ivec:computername/>'
            '<ivec:job_description><![CDATA[1]]></ivec:job_description>'
            '</ivec:param_set></ivec:contents></cmd>')


def _end_job(job=JOB_ID):
    return ('<?xml version="1.0" encoding="utf-8" ?>'
            f'<cmd {_NS}><ivec:contents><ivec:operation>EndJob</ivec:operation>'
            '<ivec:param_set servicetype="maintenance">'
            f'<ivec:jobID>{job}</ivec:jobID>'
            '</ivec:param_set></ivec:contents></cmd>')


def _operation(name, params, job=JOB_ID):
    return ('<?xml version="1.0" encoding="utf-8"?>'
            f'<cmd {_NS}><ivec:contents><ivec:operation>{name}</ivec:operation>'
            f'<ivec:param_set servicetype="maintenance">{params}'
            f'<ivec:jobID>{job}</ivec:jobID>'
            '</ivec:param_set></ivec:contents></cmd>')


def wrap(op: str) -> bytes:
    """StartJob, autant d'octets nuls que StartJob est long, l'opération, EndJob."""
    start = _start_job()
    return start.encode() + b"\x00" * len(start) + op.encode() + _end_job().encode()


def nozzle_check() -> bytes:
    return wrap(_operation("TestPrint", "<ivec:type>nozzle_check</ivec:type>"))


def cleaning(kind="regular", group="all") -> bytes:
    if kind not in ("regular", "deep") or group not in ("all", "black", "color"):
        raise ValueError("type ou groupe d'encre invalide")
    return wrap(_operation("Cleaning", f"<ivec:inkgroup>{group}</ivec:inkgroup><ivec:type>{kind}</ivec:type>"))


# Modèles sur lesquels ces commandes ont été confirmées (champ MDL, en majuscules).
# MB2100 series : Page calibrage + Nettoyage confirmés le 2026-11-09 (MB2150).
VALIDATED_MODELS = ["MB2100 SERIES", "G3000 SERIES"]

# Boutons de l'interface -> (libellé, fonction qui construit les octets)
ACTIONS = {
    "nozzle_check": ("Page calibrage", nozzle_check),
    "cleaning": ("Nettoyage", lambda: cleaning("regular", "all")),
    "deep_cleaning": ("Nettoyage en profondeur", lambda: cleaning("deep", "all")),
    "cleaning_bk": ("Nettoyage noir", lambda: cleaning("regular", "black")),
    "cleaning_cl": ("Nettoyage couleur", lambda: cleaning("regular", "color")),
}
