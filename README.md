# SAV Service Tool

Maintenance des imprimantes jet d'encre Canon depuis Windows : remise à zéro du compteur d'encre usagée (erreur 5B00),
page de test, page calibrage (vérification des buses), nettoyages des têtes, adresse IP et firmware des imprimantes du réseau.

Logiciel gratuit AKM12 — fiche et téléchargement : https://akm12.com/logiciels/sav-service-tool

## Fichiers

| Fichier | Rôle |
|---|---|
| `service_tool.py` | Interface (tkinter) et logique ; `APP_VERSION` en tête de fichier |
| `canon_reset.py` | Remise à zéro 5B00 : chiffrement, transport usbprint.sys, profils de modèles, `self_test()` |
| `canon_ivec.py` | Commandes de maintenance IVEC (page calibrage, nettoyages) |
| `canon_network.py` | Découverte BJNP des imprimantes du réseau local |
| `printer_io.py` | Files d'impression Windows et impression RAW |
| `commands.json` | Catalogue des commandes ; recréé par l'exe s'il manque |
| `THIRD_PARTY_NOTICES.txt` | Licences zlib et MIT des projets repris : à distribuer avec l'exe |

## Construire

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1   # → release\SAVServiceTool-<version>-windows.zip
```

Python 3 et PyInstaller sont nécessaires. Aucune autre dépendance : uniquement la bibliothèque standard.

- Icône : `py assets\make_icon.py` (écrit `sav.ico` et `sav-256.png`).
- Guide PDF (Pillow et reportlab nécessaires) : `py docs\build\shots.py docs\build\shots` (captures sur imprimante
  de démonstration, rien n'est envoyé), convertir les PNG en JPG, puis
  `py docs\build\make_pdf.py docs\build\shots docs\Guide_SAV_Service_Tool-<version>.pdf`.
- Nouvelle version : `APP_VERSION` (service_tool.py), `version_info.txt` et `VERSION` (docs/build/make_pdf.py).

## Modèles validés

- Remise à zéro 5B00 : MAXIFY MB2100 / MB2150 (firmware 1.130), G6000 / G6020.
- Page calibrage et nettoyages : MAXIFY MB2100 / MB2150 (confirmé) ; G3000 series (trames du projet canon-ij-maint).

Les fonctions de la page « Avancé » dont la trame n'est pas connue (`"status": "missing"` dans `commands.json`)
refusent de s'exécuter.

Logiciel indépendant, non édité ni approuvé par Canon.

## Licence

Code consultable, tous droits réservés — voir [LICENSE](LICENSE). Vous pouvez lire, cloner et compiler ce code
pour votre propre usage ; sa redistribution, sa modification publiée et sa réutilisation demandent l'accord
d'AKM12. Les versions officielles gratuites sont publiées sur https://akm12.com et
https://github.com/akm12-dev/releases.
