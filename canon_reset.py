"""Remise à zéro du compteur d'encre usagée (erreur 5B00) - imprimantes Canon.

Protocole, algorithme de chiffrement et tables du profil G6000 portés depuis
le projet open source « canon-megatank-reset » (Jess Sullivan, licence zlib) :
https://github.com/Jesssullivan/canon-megatank-reset
Validé par l'auteur sur une Canon G6020 (série G6000).

Transport : IOCTL VENDOR_SET / VENDOR_GET du pilote Windows usbprint.sys
(le même chemin que l'outil de service d'origine), donc aucun pilote à installer.

Séquence (imprimante en MODE SERVICE) :
  1. set_session  81 00 00 03                 (OUT)
  2. get_keyword  82 00 00     -> clé de session (IN)
  3. set_command  85 00 00 | 10 07 7c  chiffré (sélection ligne « waste »)
  4. set_command  85 00 00 | 0d RR 00  chiffré (RAZ absorbeur RR)
  5. get_command  86 00 00                   (lecture, réponse vide = normal)
Puis extinction PROPRE par le bouton marche (sinon la RAZ n'est pas enregistrée).
"""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass

# =========================================================== profils modèles
# Chaque profil contient les tables de chiffrement propres à une famille.
# N'AJOUTEZ un profil que si ses tables proviennent d'une source vérifiée :
# des tables fausses produisent des commandes que l'imprimante interprète mal.

_G6000_FUNCS = {
    0x00: ((0x04, 0x66), ()), 0x01: ((0x05, 0x22), (0x07,)), 0x02: ((0x00, 0x87), ()),
    0x03: ((0x0F, 0x01), (0x03,)), 0x04: ((0x09, 0xA3), (0x08,)), 0x05: ((0x07, 0x66), ()),
    0x06: ((0x01, 0x81), ()), 0x07: ((0x04, 0x0F), (0x01, 0x03)), 0x08: ((0x0B, 0x91), (0x06, 0x01)),
    0x09: ((0x02, 0x22), (0x07, 0x0A)), 0x0A: ((0x06, 0x02), ()), 0x0B: ((0x06, 0xCC), (0x02, 0x0D)),
    0x0C: ((0x02, 0xA8), ()), 0x0D: ((0x05, 0x01), (0x03, 0x04)), 0x0E: ((0x0A, 0x10), (0x0B,)),
    0x0F: ((0x02, 0x02), (0x01,)), 0x10: ((0x01, 0xDD), (0x09, 0x05)), 0x11: ((0x00, 0xB4), (0x0C,)),
    0x12: ((0x03, 0x3A), (0x02, 0x0A)), 0x13: ((0x01, 0xAA), (0x05,)), 0x14: ((0x07, 0x03), (0x06,)),
    0x15: ((0x03, 0x6D), ()),
}

PROFILES = {
    "G6000": {
        "label": "Méthode 3 - G6000 series, MAXIFY MB2100 series",
        "match": ["G6000 SERIES", "MB2100 SERIES"],  # champ MDL: de l'identifiant IEEE-1284
        "validated": ("G6020 (projet canon-megatank-reset) ; "
                      "MB2150 fw 1.130, absorbeur Main, 5B00 effacée le 2026-11-09 (SAV)"),
        "absorbers": {"Main": 0x00},  # absorbeur 'common' : seul validé
        "keyword_codes": bytes.fromhex("4D495300"),
        "keyword_index": (3, 1, 0, 2),
        "command_index": [bytes.fromhex(h) for h in (
            "0F03130C01080012070510040E0602110B0D090A",
            "081200060F040B0E010A0213030511070D09100C",
            "040B130907110F020D00010E05030610080A0C12",
            "120E000F07080B011303110210040D090C060A05",
            "0705080A1103000E131204010906020D0F0B0C10")],
        "command_codes": [bytes.fromhex(h) for h in (
            "0912DD1D4113636B442A17BDAFD288313B71BBE5",
            "BB412CD2188977454F11056725D37C4ED44A8891",
            "3F03263DCA72894409E2B820A94E2B040C696B25",
            "6812637F8FDE7040382F096481BB31C51A726D3A",
            "CACC1DE4781C1B7E7F14D518D1CF807B02D319DE",
            "142722080A9DA7CAE83A4B476B899590236FB2C7",
            "38422F4F6D709BDDE6090507F012A817624C3195")],
        # 3 tableaux de « shift », chacun = 4 programmes (liste de (op, valeur))
        "command_shift": [
            [[("=", 0)], [("&", 1)], [("=", 0)], [("=", 0)]],
            [[("&", 1)], [("=", 1)], [("%", 5)], [("=", 0)]],
            [[("&", 1)], [("=", 0)], [("=", 0)], [("=", 2)]],
        ],
        "functions": _G6000_FUNCS,
    },
}

# Valeurs de contrôle (trames réelles capturées, clé e4 7c 5a) pour l'autotest.
_SELFTEST = {
    "G6000": (bytes.fromhex("e47c5a00"),
              "850000dbbb006759a1b01f842fd583044a3ac351d2b1ef",
              "8500004dbb006759a1b01f842fd58319a83a627bafb1ef"),
}

COMMIT_INSTRUCTION = (
    "Pour ENREGISTRER la remise à zéro : éteignez l'imprimante avec le BOUTON MARCHE "
    "(ne débranchez pas le câble secteur). Rallumez-la ensuite normalement."
)


class ResetError(Exception):
    pass


# =========================================================== chiffrement
_ENVELOPE_FIXED = bytes.fromhex("e93f0da196953104492d9e6183cf096f")  # LCG MSVC, graine 0x12345678


def _apply_shift(seed, prog):
    acc = seed
    for op, d in prog:
        if op == "=": acc = d
        elif op == "+": acc = acc + d
        elif op == "-": acc = acc - d
        elif op == "*": acc = acc * d
        elif op == "/": acc = acc // d if d else 0
        elif op == "%": acc = acc % d if d else 0
        elif op == "&": acc &= d
        elif op == "|": acc |= d
        elif op == "^": acc ^= d
        acc &= 0xFFFFFFFF
    return acc


def _bind_keyword(p, device_kw):
    return bytes((p["keyword_codes"][j] ^ device_kw[j]) & 0xFF for j in p["keyword_index"])


def _functor2(p, subject, seed_src):
    seed = 0
    for b in seed_src:
        seed = (seed * 256 + b) & 0xFFFFFFFF
    idx = p["command_index"][seed % len(p["command_index"])]
    codes = p["command_codes"][seed % len(p["command_codes"])]
    shifts = [_apply_shift(seed, prog) for prog in p["command_shift"][seed % len(p["command_shift"])]]
    n = len(subject)
    out = bytearray(n)
    for i in range(n):
        j = idx[i % len(idx)] % n
        ks = ((seed >> (shifts[j % len(shifts)] & 0x1F)) ^ codes[j % len(codes)]) & 0xFF
        out[i] = subject[j] ^ ks
    return bytes(out)


def _envelope(p, frame):
    env = bytearray([0x00, 0x12, 0x01, frame[3]]) + bytearray(_ENVELOPE_FIXED)
    blk = p["functions"].get(frame[3])
    if blk:
        special, indexes = blk
        for k in range(0, len(special) - 1, 2):
            if 4 + special[k] < len(env):
                env[4 + special[k]] = special[k + 1]
        for i, off in enumerate(indexes):
            if i < len(frame) - 4 and 4 + off < len(env):
                env[4 + off] = frame[4 + i]
    return bytes(env)


def encipher_set_command(p, operand: bytes, device_kw: bytes) -> bytes:
    """Trame 23 octets : 85 00 00 || chiffré(enveloppe(85 00 00 || operand))."""
    frame = b"\x85\x00\x00" + operand
    return frame[:3] + _functor2(p, _envelope(p, frame), _bind_keyword(p, device_kw))


def self_test():
    """Vérifie que le chiffrement reproduit les trames réelles capturées."""
    for name, (kw, sel, clr) in _SELFTEST.items():
        p = PROFILES[name]
        if encipher_set_command(p, bytes.fromhex("10077c"), kw).hex() != sel:
            raise ResetError(f"Autotest chiffrement {name} : trame SELECT incorrecte")
        if encipher_set_command(p, bytes.fromhex("0d0000"), kw).hex() != clr:
            raise ResetError(f"Autotest chiffrement {name} : trame CLEAR incorrecte")
    return True


# =========================================================== USB (usbprint.sys)
_setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


GUID_DEVINTERFACE_USBPRINT = GUID(0x28D78FAD, 0x5A12, 0x11D1,
                                  (ctypes.c_ubyte * 8)(0xAE, 0x5B, 0x00, 0x00, 0xF8, 0x03, 0xA8, 0xC2))


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("InterfaceClassGuid", GUID),
                ("Flags", wintypes.DWORD), ("Reserved", ctypes.c_void_p)]


_setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
_setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD]
_setupapi.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID),
                                                  wintypes.DWORD, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
_setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
                                                       ctypes.c_void_p, wintypes.DWORD,
                                                       ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
_setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
_k32.CreateFileW.restype = wintypes.HANDLE
_k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                             wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
_k32.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
_k32.CloseHandle.argtypes = [wintypes.HANDLE]

IOCTL_GET_1284_ID = 0x220034
IOCTL_VENDOR_SET = 0x220038
IOCTL_VENDOR_GET = 0x22003C
INVALID_HANDLE = wintypes.HANDLE(-1).value


def _winerr(where):
    c = ctypes.get_last_error()
    return ResetError(f"{where} : erreur Windows {c} ({ctypes.FormatError(c).strip()})")


def list_usb_printers():
    """Chemins des interfaces USB-imprimante présentes (usbprint.sys)."""
    h = _setupapi.SetupDiGetClassDevsW(ctypes.byref(GUID_DEVINTERFACE_USBPRINT), None, None, 0x12)
    if not h or h == INVALID_HANDLE:
        raise _winerr("SetupDiGetClassDevs")
    paths = []
    try:
        i = 0
        while True:
            ifd = SP_DEVICE_INTERFACE_DATA()
            ifd.cbSize = ctypes.sizeof(ifd)
            if not _setupapi.SetupDiEnumDeviceInterfaces(h, None, ctypes.byref(GUID_DEVINTERFACE_USBPRINT),
                                                         i, ctypes.byref(ifd)):
                break
            need = wintypes.DWORD()
            _setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(ifd), None, 0, ctypes.byref(need), None)
            buf = ctypes.create_string_buffer(need.value)
            ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            if _setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(ifd), buf, need, None, None):
                paths.append(ctypes.wstring_at(ctypes.addressof(buf) + 4))
            i += 1
    finally:
        _setupapi.SetupDiDestroyDeviceInfoList(h)
    return paths


class OVERLAPPED(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_void_p), ("InternalHigh", ctypes.c_void_p),
                ("Offset", wintypes.DWORD), ("OffsetHigh", wintypes.DWORD), ("hEvent", wintypes.HANDLE)]


_k32.CreateEventW.restype = wintypes.HANDLE
_k32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
_k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_k32.WaitForSingleObject.restype = wintypes.DWORD
_k32.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                           ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
_k32.CancelIoEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_k32.GetOverlappedResult.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL]

IO_TIMEOUT_MS = 5000


class UsbPrinter:
    def __init__(self, path):
        self.path = path
        self.h = _k32.CreateFileW(path, 0xC0000000, 0x3, None, 3, 0x40000000, None)  # OVERLAPPED
        if self.h == INVALID_HANDLE or not self.h:
            raise _winerr("Ouverture du périphérique USB")

    def close(self):
        if self.h:
            _k32.CloseHandle(self.h)
            self.h = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def _ioctl(self, code, inbuf: bytes, out_len: int):
        ib = ctypes.create_string_buffer(inbuf, len(inbuf)) if inbuf else None
        ob = ctypes.create_string_buffer(out_len) if out_len else None
        ret = wintypes.DWORD()
        ov = OVERLAPPED()
        ov.hEvent = _k32.CreateEventW(None, True, False, None)
        try:
            if not _k32.DeviceIoControl(self.h, code, ib, len(inbuf), ob, out_len, ctypes.byref(ret), ctypes.byref(ov)):
                if ctypes.get_last_error() != 997:  # ERROR_IO_PENDING
                    raise _winerr(f"DeviceIoControl 0x{code:06X}")
                if _k32.WaitForSingleObject(ov.hEvent, IO_TIMEOUT_MS) != 0:
                    _k32.CancelIoEx(self.h, ctypes.byref(ov))
                    _k32.GetOverlappedResult(self.h, ctypes.byref(ov), ctypes.byref(ret), True)
                    raise ResetError(f"L'imprimante ne répond pas (délai {IO_TIMEOUT_MS // 1000} s dépassé, "
                                     f"commande 0x{code:06X}).")
                if not _k32.GetOverlappedResult(self.h, ctypes.byref(ov), ctypes.byref(ret), False):
                    raise _winerr(f"DeviceIoControl 0x{code:06X}")
        finally:
            _k32.CloseHandle(ov.hEvent)
        return ob.raw[:ret.value] if ob else b""

    def write(self, data: bytes, timeout_ms=15000) -> int:
        """Écrit des données d'impression (canal bulk OUT), avec délai maximum."""
        buf = ctypes.create_string_buffer(data, len(data))
        n = wintypes.DWORD()
        ov = OVERLAPPED()
        ov.hEvent = _k32.CreateEventW(None, True, False, None)
        try:
            if not _k32.WriteFile(self.h, buf, len(data), ctypes.byref(n), ctypes.byref(ov)):
                if ctypes.get_last_error() != 997:
                    raise _winerr("Écriture USB")
                if _k32.WaitForSingleObject(ov.hEvent, timeout_ms) != 0:
                    _k32.CancelIoEx(self.h, ctypes.byref(ov))
                    _k32.GetOverlappedResult(self.h, ctypes.byref(ov), ctypes.byref(n), True)
                    raise ResetError("L'imprimante n'accepte pas les données (occupée, en erreur ou sans papier ?).")
                if not _k32.GetOverlappedResult(self.h, ctypes.byref(ov), ctypes.byref(n), False):
                    raise _winerr("Écriture USB")
        finally:
            _k32.CloseHandle(ov.hEvent)
        return n.value

    def device_id(self) -> str:
        raw = self._ioctl(IOCTL_GET_1284_ID, b"", 1024)
        return raw[2:].decode("latin-1", "replace") if len(raw) > 2 else ""

    def vendor_set(self, frame: bytes):
        self._ioctl(IOCTL_VENDOR_SET, frame, 0)

    def vendor_get(self, header: bytes, length=64) -> bytes:
        return self._ioctl(IOCTL_VENDOR_GET, header, length)


# =========================================================== haut niveau
@dataclass
class Detected:
    path: str
    vid: str
    pid: str
    device_id: str
    model: str
    profile: str | None


def _field(device_id, key):
    for part in device_id.split(";"):
        k, _, v = part.partition(":")
        if k.strip().upper() in (key, {"MDL": "MODEL", "MFG": "MANUFACTURER"}.get(key, "")):
            return v.strip()
    return ""


def match_profile(model: str):
    m = model.upper()
    for name, p in PROFILES.items():
        if any(s in m for s in p["match"]):
            return name
    return None


def detect():
    """Lecture seule : liste les imprimantes Canon USB et leur modèle."""
    found = []
    for path in list_usb_printers():
        low = path.lower()
        vid = low.split("vid_")[1][:4] if "vid_" in low else "?"
        pid = low.split("pid_")[1][:4] if "pid_" in low else "?"
        try:
            with UsbPrinter(path) as d:
                did = d.device_id()
        except ResetError as e:
            did = f"(lecture impossible : {e})"
        model = _field(did, "MDL")
        if vid != "04a9" and "canon" not in did.lower():
            continue
        found.append(Detected(path, vid, pid, did, model, match_profile(model)))
    return found


# Codes d'absorbeur de la table « functions.waste » (base de modèles d'origine).
WASTE_REGIONS = {"Main": 0x00, "Platen": 0x01, "Black": 0x03, "Color": 0x04, "Away": 0x05, "Home": 0x06}


def reset_absorber(path: str, profile_name: str, absorber: str = "Main", force=False, log=print):
    """Exécute la séquence de RAZ. L'imprimante doit être en mode service.

    force=True : modèle sans profil validé, on tente le protocole du profil donné."""
    p = PROFILES[profile_name]
    regions = WASTE_REGIONS if force else p["absorbers"]
    if absorber not in regions:
        raise ResetError(f"Absorbeur « {absorber} » non pris en charge par le profil {profile_name}.")
    self_test()
    region = regions[absorber]
    with UsbPrinter(path) as d:
        log("1/5 Ouverture de la session de service…")
        d.vendor_set(bytes.fromhex("81000003"))
        log("2/5 Lecture de la clé de session…")
        kw = d.vendor_get(bytes.fromhex("820000"), 64)
        log(f"    clé reçue : {kw.hex(' ') or '(vide)'}")
        if len(kw) < 3:
            raise ResetError("Aucune clé de session reçue : l'imprimante n'est probablement pas "
                             "en mode service (ou ce modèle n'utilise pas ce protocole). Rien n'a été écrit.")
        kw = (kw[:4] + b"\x00" * 4)[:4]
        log("3/5 Sélection du compteur d'encre usagée…")
        d.vendor_set(encipher_set_command(p, bytes([0x10, 0x07, 0x7C]), kw))
        log(f"4/5 Remise à zéro de l'absorbeur « {absorber} »…")
        d.vendor_set(encipher_set_command(p, bytes([0x0D, region, 0x00]), kw))
        log("5/5 Lecture de contrôle…")
        try:
            r = d.vendor_get(bytes.fromhex("860000"), 64)
            log(f"    réponse : {r.hex(' ') or '(vide - normal)'}")
        except ResetError as e:
            log(f"    lecture de contrôle ignorée ({e})")
    log("Commandes envoyées. " + COMMIT_INSTRUCTION)
