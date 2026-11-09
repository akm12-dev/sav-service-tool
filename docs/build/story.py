"""Contenu du guide SAV Service Tool (importé par make_pdf.py, qui fournit les fonctions de mise en page)."""

TOC = [
    ("intro", "Présentation, prérequis et précautions"),
    ("install", "Installation et premier lancement"),
    ("dash", "Tableau de bord"),
    ("maint", "Entretien : page de test, page calibrage, nettoyages"),
    ("reset", "Erreur 5B00 : remise à zéro du compteur d'encre usagée"),
    ("net", "Réseau et firmware"),
    ("adv", "Page Avancé"),
    ("depannage", "Dépannage"),
    ("securite", "Journal, licences et désinstallation"),
]


def build(pages, L):
    """L : module make_pdf (P, section, box, table, code, shot, steps, bullets, W, cm, Spacer, PageBreak…)."""
    P, section, box, table, code, shot, steps, bullets = (L.P, L.section, L.box, L.table, L.code, L.shot,
                                                          L.steps, L.bullets)
    W, cm, Spacer, PageBreak, NextPageTemplate = L.W, L.cm, L.Spacer, L.PageBreak, L.NextPageTemplate
    V = L.VERSION
    S = []
    add, ext = S.append, S.extend

    # ---------------------------------------------------------- couverture
    add(NextPageTemplate("main"))
    add(P("Ce que fait le logiciel", "h2"))
    add(P("SAV Service Tool regroupe les opérations d'atelier sur les imprimantes jet d'encre Canon : remise à zéro "
          "du compteur d'encre usagée (erreur 5B00), page de test, page calibrage, nettoyages des têtes, et "
          "recherche des imprimantes du réseau avec leur adresse IP et leur firmware."))
    add(Spacer(1, 6))
    rows = [["Section", "Contenu", "Page"]]
    for i, (key, title) in enumerate(TOC, 1):
        rows.append([str(i), title, str(pages.get(key, ""))])
    add(table(rows, [2 * cm, W - 4 * cm, 2 * cm]))
    add(Spacer(1, 10))
    add(P("Les captures de ce guide utilisent une imprimante de démonstration (MAXIFY MB2100 series, adresses "
          "IP et MAC fictives).", "small"))
    add(PageBreak())

    # ---------------------------------------------------------- 1
    ext(section(1, "intro", "Présentation, prérequis et précautions"))
    add(P("Le logiciel s'organise en cinq écrans, accessibles depuis le menu de gauche :"))
    add(table([["Écran", "À quoi il sert"],
               ["Tableau de bord", "État de l'imprimante USB (modèle, mode), adresse IP, firmware, et actions rapides."],
               ["Entretien", "Page de test Windows, page calibrage (vérification des buses), nettoyages."],
               ["Erreur 5B00", "Remise à zéro du compteur d'encre usagée, avec la marche à suivre."],
               ["Réseau & firmware", "Imprimantes Canon du réseau local, interface web, mise à jour du firmware."],
               ["Avancé", "Fonctions de l'outil de service d'origine, pour la plupart non disponibles."]],
              [3.8 * cm, W - 3.8 * cm]))
    add(P("Modèles validés", "h2"))
    add(table([["Fonction", "Modèles validés"],
               ["Remise à zéro 5B00", "MAXIFY MB2100 / MB2150 (firmware 1.130, absorbeur Main) ; G6000 / G6020."],
               ["Page calibrage et nettoyages", "MAXIFY MB2100 / MB2150."],
               ["Page de test", "Toute imprimante installée dans Windows (page de test du pilote)."],
               ["Recherche réseau", "Imprimantes Canon répondant au protocole BJNP, sur le même réseau que le PC."]],
              [4.6 * cm, W - 4.6 * cm]))
    add(P("Sur un autre modèle, le logiciel refuse la remise à zéro tant que l'option « Forcer » n'est pas cochée. "
          "Les nettoyages et la page calibrage restent possibles, avec un avertissement dans le journal."))
    add(P("Prérequis", "h2"))
    ext(bullets([
        "Windows 10 ou 11.",
        "Imprimante branchée en USB pour la remise à zéro, la page calibrage et les nettoyages. Aucun pilote "
        "supplémentaire n'est nécessaire : le logiciel utilise le pilote USB d'impression de Windows.",
        "Pour la page de test : l'imprimante installée dans Windows (sa file d'impression).",
        "Pour la recherche réseau : le PC et l'imprimante sur le même réseau local.",
    ]))
    add(box(["<b>Le compteur d'encre usagée protège l'imprimante.</b> Il indique que les tampons qui absorbent "
             "l'encre des nettoyages sont pleins. Remettre le compteur à zéro sans remplacer ou nettoyer ces "
             "tampons peut provoquer un débordement d'encre dans l'imprimante et sur le meuble.",
             "Ce logiciel est indépendant : il n'est ni édité ni approuvé par Canon."], "warn"))

    # ---------------------------------------------------------- 2
    ext(section(2, "install", "Installation et premier lancement"))
    add(P(f"Le logiciel se télécharge depuis <b>akm12.com/logiciels/sav-service-tool</b> sous la forme d'une "
          f"archive <b>SAVServiceTool-{V}-windows.zip</b>. Il ne s'installe pas : il se lance depuis un dossier "
          "ou une clé USB d'intervention."))
    add(table([["Fichier de l'archive", "Rôle"],
               ["SAVServiceTool.exe", "Le logiciel."],
               ["commands.json", "Catalogue des commandes. S'il manque, le logiciel le recrée."],
               ["THIRD_PARTY_NOTICES.txt", "Licences des projets open source repris : à conserver avec le logiciel."],
               ["LISEZMOI.txt", "Démarrage rapide et procédure 5B00."]],
              [5 * cm, W - 5 * cm]))
    add(P("Vérifier le fichier téléchargé", "h2"))
    add(P("L'empreinte SHA-256 de l'archive est publiée sur la fiche du logiciel. Dans PowerShell, depuis le dossier "
          "Téléchargements :"))
    add(code([f"Get-FileHash .\\SAVServiceTool-{V}-windows.zip -Algorithm SHA256"]))
    add(Spacer(1, 6))
    add(P("Démarrer", "h2"))
    ext(steps([
        "Clic droit sur l'archive, <b>Extraire tout…</b>, puis choisissez un dossier. Gardez les fichiers ensemble.",
        "Branchez l'imprimante en USB et allumez-la.",
        "Double-cliquez sur <b>SAVServiceTool.exe</b>. Si Windows SmartScreen affiche « Windows a protégé votre "
        "ordinateur » : <b>Informations complémentaires</b>, puis <b>Exécuter quand même</b>.",
        "Au démarrage, le logiciel vérifie son chiffrement 5B00 (« Autotest chiffrement 5B00 : OK » dans le "
        "journal), détecte l'imprimante USB et recherche les imprimantes du réseau.",
    ]))

    # ---------------------------------------------------------- 3
    ext(section(3, "dash", "Tableau de bord"))
    add(shot("1_tableau_de_bord.jpg", "Tableau de bord : imprimante détectée en mode normal."))
    add(P("Les quatre cartes du haut, visibles sur tous les écrans, résument l'état de l'imprimante :"))
    add(table([["Carte", "Signification"],
               ["Imprimante USB", "Modèle détecté en USB, ou « Non connectée »."],
               ["Adresse IP", "Adresse trouvée par la recherche réseau, ou « non trouvée »."],
               ["Firmware", "Version du firmware lue sur l'imprimante (USB ou réseau)."],
               ["Mode", "<b>Normal</b> (vert) pour l'utilisation courante, <b>Service</b> (orange) pour la remise "
                        "à zéro 5B00."]],
              [3.4 * cm, W - 3.4 * cm]))
    add(P("Les tuiles ouvrent directement les actions courantes. <b>Actualiser</b> relit les files d'impression, "
          "l'imprimante USB et le réseau, par exemple après avoir branché une autre imprimante."))

    # ---------------------------------------------------------- 4
    ext(section(4, "maint", "Entretien : page de test, page calibrage, nettoyages"))
    add(shot("2_entretien.jpg", "Écran Entretien."))
    add(P("Impression", "h2"))
    ext(bullets([
        "<b>File d'impression</b> : l'imprimante telle qu'elle est installée dans Windows. Avec « Canon USB "
        "uniquement », seules les files Canon branchées en USB sont proposées. Les files « FAX » sont toujours "
        "exclues, pour qu'une page de test ne parte jamais en télécopie.",
        "<b>Page de test</b> : la page de test de Windows, imprimée par le pilote. Elle vérifie que l'imprimante et "
        "son pilote fonctionnent.",
        "<b>Page calibrage</b> : le motif de vérification des buses, envoyé directement à l'imprimante en USB. "
        "Des traits manquants ou des couleurs pâles indiquent des buses bouchées : lancez un nettoyage.",
    ]))
    add(P("Nettoyage", "h2"))
    add(table([["Bouton", "Effet"],
               ["Nettoyage", "Nettoyage normal de toutes les têtes."],
               ["Nettoyage noir / couleur", "Nettoyage limité aux têtes noires ou couleur : moins d'encre consommée."],
               ["Nettoyage profond", "Nettoyage intensif, avec confirmation. Il consomme beaucoup d'encre et "
                                     "remplit les tampons d'encre usagée : à utiliser seulement si deux "
                                     "nettoyages normaux n'ont pas suffi."]],
              [4.4 * cm, W - 4.4 * cm]))
    add(box("Laissez l'imprimante terminer un nettoyage (une à deux minutes) avant d'imprimer une nouvelle page "
            "calibrage pour contrôler le résultat.", "tip"))

    # ---------------------------------------------------------- 5
    ext(section(5, "reset", "Erreur 5B00 : remise à zéro du compteur d'encre usagée"))
    add(P("L'imprimante affiche l'erreur <b>5B00</b> (ou 5B01, 1700) quand son compteur d'encre usagée atteint la "
          "limite : elle refuse alors d'imprimer. La remise à zéro se fait en <b>mode service</b>, un mode de "
          "maintenance de l'imprimante."))
    add(box("Avant toute remise à zéro, remplacez ou nettoyez les tampons d'encre usagée.", "warn"))
    add(shot("3_5b00_normal.jpg", "Étape 2 : « Détecter » en mode normal ; le modèle est pris en charge."))
    ext(steps([
        "<b>Remplacez ou nettoyez les tampons d'encre usagée.</b>",
        "Imprimante allumée et branchée en USB, cliquez sur <b>Détecter</b>. Le modèle s'affiche avec "
        "« Modèle pris en charge pour la remise à zéro » (en vert). Le logiciel mémorise ce modèle : en mode service, "
        "l'imprimante ne donne plus son nom.",
        "Passez l'imprimante en mode service (MAXIFY MB2150) : éteignez-la, câble USB branché. Maintenez le "
        "<b>bouton STOP orange</b> (rond, à côté du triangle d'avertissement), maintenez aussi <b>ON</b>, relâchez STOP, "
        "appuyez <b>5 fois</b> sur STOP, puis relâchez ON. L'écran reste vide ; Windows peut détecter un nouveau "
        "périphérique.",
        "Cliquez de nouveau sur <b>Détecter</b> : la carte Mode doit indiquer <b>Service</b> (orange) et la liste "
        "afficher « (mode service) ».",
        "Laissez l'absorbeur sur <b>Main</b>, cliquez sur <b>Remettre le compteur à zéro</b> et confirmez. Le "
        "journal affiche les étapes 1/5 à 5/5.",
        "<b>Éteignez l'imprimante avec le bouton ON</b>, sans la débrancher, puis rallumez-la : c'est cette "
        "extinction qui enregistre la remise à zéro. L'erreur 5B00 a disparu.",
    ]))
    add(shot("4_5b00_service.jpg", "Étape 4 : l'imprimante est en mode service, prête pour la remise à zéro."))
    add(P("Bon à savoir", "h2"))
    ext(bullets([
        "La séquence du mode service varie selon les modèles (2 à 6 appuis sur STOP). Le menu « ? › Mode service… » du "
        "logiciel rappelle la séquence la plus courante.",
        "Seul l'absorbeur <b>Main</b> a été validé. « Platen » est proposé mais non vérifié.",
        "<b>Forcer le protocole</b> applique la méthode G6000 à un modèle non validé. À réserver aux essais : si "
        "l'imprimante refuse (erreur 31 à l'étape 3 alors qu'elle est bien en mode service), ce modèle utilise un "
        "autre protocole ; n'insistez pas.",
        "La remise à zéro a été validée sur le firmware <b>1.130</b> du MB2150. Une mise à jour du firmware peut "
        "la bloquer définitivement : désactivez la mise à jour automatique sur les imprimantes concernées.",
    ]))

    # ---------------------------------------------------------- 6
    ext(section(6, "net", "Réseau et firmware"))
    add(shot("5_reseau.jpg", "Imprimantes Canon trouvées sur le réseau local (adresses fictives)."))
    add(P("<b>Rechercher</b> interroge le réseau local (protocole BJNP de Canon) et liste chaque imprimante avec son "
          "adresse IP, son modèle, son firmware et son adresse MAC. Seules les imprimantes du même réseau que le PC "
          "répondent. <b>Interface web</b> ouvre la page de configuration de l'imprimante dans le navigateur."))
    add(P("Mise à jour du firmware", "h2"))
    add(P("Le bouton <b>Mise à jour du firmware…</b> affiche un avertissement, puis ouvre l'interface web de "
          "l'imprimante : c'est l'imprimante elle-même qui télécharge et installe le firmware officiel. Le logiciel "
          "n'installe jamais de firmware."))
    add(box("Ne mettez pas à jour le firmware d'une imprimante dont vous voulez pouvoir remettre le compteur à zéro, "
            "et ne coupez jamais le courant pendant une mise à jour.", "warn"))

    # ---------------------------------------------------------- 7
    ext(section(7, "adv", "Page Avancé"))
    add(shot("6_avance.jpg", "Page Avancé."))
    add(P("Cette page reprend les sections de l'outil de service d'origine (EEPROM, Set Destination, compteurs…). "
          "Les commandes dont la trame n'est pas connue sont marquées « missing » dans <b>commands.json</b> : leur "
          "bouton affiche un message et n'envoie rien à l'imprimante. Les fonctions validées se trouvent dans les "
          "écrans Entretien et Erreur 5B00."))

    # ---------------------------------------------------------- 8
    ext(section(8, "depannage", "Dépannage"))
    add(table([["Symptôme", "Cause probable et solution"],
               ["« Aucune imprimante Canon USB détectée »", "Câble USB débranché ou imprimante éteinte. Essayez un "
                "autre port USB, attendez que Windows ait reconnu l'imprimante, puis « Détecter »."],
               ["Modèle non validé", "Le modèle n'a pas de profil de remise à zéro. Les nettoyages restent "
                "possibles ; la remise à zéro demande « Forcer » (voir section 5)."],
               ["Mode toujours « Normal »", "La séquence du mode service n'a pas abouti : recommencez depuis "
                "l'imprimante éteinte, en comptant les appuis sur STOP."],
               ["Erreur 31 à l'étape 3/5", "L'imprimante n'est pas en mode service, ou ce modèle utilise un autre "
                "protocole. Rien n'a été modifié."],
               ["5B00 toujours affichée", "L'imprimante a été débranchée au lieu d'être éteinte avec ON, ou un autre "
                "absorbeur est plein. Refaites la procédure et éteignez avec ON."],
               ["Aucune imprimante sur le réseau", "PC et imprimante sur des réseaux différents (Wi-Fi invité, autre "
                "sous-réseau) ou pare-feu bloquant le port UDP 8611."],
               ["« Impossible de lire commands.json »", "Fichier modifié ou abîmé : supprimez-le, le logiciel le "
                "recrée au prochain démarrage."],
               ["Fenêtre SmartScreen", "Normal pour un fichier non signé : vérifiez l'empreinte SHA-256, puis "
                "Informations complémentaires › Exécuter quand même."]],
              [4.6 * cm, W - 4.6 * cm]))
    add(Spacer(1, 8))
    add(P("Pour signaler un problème : <b>github.com/akm12-dev/releases/issues</b>. Indiquez le modèle de "
          "l'imprimante, son firmware, la version du logiciel et joignez le fichier <b>service_tool.log</b>."))

    # ---------------------------------------------------------- 9
    ext(section(9, "securite", "Journal, licences et désinstallation"))
    ext(bullets([
        "Le journal s'affiche en bas de chaque écran et est enregistré dans <b>service_tool.log</b>, à côté du "
        "logiciel. Le dernier modèle détecté est gardé dans <b>last_model.txt</b>.",
        "Le logiciel fonctionne en local : il n'envoie aucune donnée, ne demande pas de compte et n'accède à "
        "internet que si vous ouvrez l'interface web d'une imprimante.",
        "Il reprend du code open source : canon-megatank-reset (licence zlib, Jess Sullivan) pour la remise à zéro "
        "et canon-ij-maint (licence MIT, Taktek et Nizar Mahmoud) pour les commandes de maintenance. Les textes de "
        "licence sont dans THIRD_PARTY_NOTICES.txt.",
        "Canon, MAXIFY et PIXMA sont des marques de Canon Inc. SAV Service Tool n'est ni édité ni approuvé par Canon.",
    ]))
    add(P("Désinstaller", "h2"))
    add(P("Supprimez le dossier du logiciel : il n'installe rien dans Windows."))
    add(Spacer(1, 10))
    add(box("SAV Service Tool est gratuit, sans inscription. Téléchargez-le uniquement depuis akm12.com ou "
            "github.com/akm12-dev/releases, et vérifiez son empreinte SHA-256.", "tip", "Logiciel gratuit AKM12"))
    return S
