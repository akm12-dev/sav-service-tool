"""Communication bas niveau avec les imprimantes Windows (spouleur, mode RAW).

Utilise uniquement ctypes + winspool.drv : aucune dépendance externe.
Les données sont envoyées telles quelles (type "RAW") à l'imprimante, sans
passer par le pilote, ce qui permet d'envoyer des commandes de maintenance.
"""
import ctypes
from ctypes import wintypes

winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)

PRINTER_ENUM_LOCAL = 0x2
PRINTER_ENUM_CONNECTIONS = 0x4


class PRINTER_INFO_2(ctypes.Structure):
    _fields_ = [
        ("pServerName", wintypes.LPWSTR), ("pPrinterName", wintypes.LPWSTR),
        ("pShareName", wintypes.LPWSTR), ("pPortName", wintypes.LPWSTR),
        ("pDriverName", wintypes.LPWSTR), ("pComment", wintypes.LPWSTR),
        ("pLocation", wintypes.LPWSTR), ("pDevMode", ctypes.c_void_p),
        ("pSepFile", wintypes.LPWSTR), ("pPrintProcessor", wintypes.LPWSTR),
        ("pDatatype", wintypes.LPWSTR), ("pParameters", wintypes.LPWSTR),
        ("pSecurityDescriptor", ctypes.c_void_p), ("Attributes", wintypes.DWORD),
        ("Priority", wintypes.DWORD), ("DefaultPriority", wintypes.DWORD),
        ("StartTime", wintypes.DWORD), ("UntilTime", wintypes.DWORD),
        ("Status", wintypes.DWORD), ("cJobs", wintypes.DWORD),
        ("AveragePPM", wintypes.DWORD),
    ]


class DOC_INFO_1(ctypes.Structure):
    _fields_ = [("pDocName", wintypes.LPWSTR), ("pOutputFile", wintypes.LPWSTR),
                ("pDatatype", wintypes.LPWSTR)]


winspool.EnumPrintersW.argtypes = [wintypes.DWORD, wintypes.LPWSTR, wintypes.DWORD,
                                   ctypes.c_void_p, wintypes.DWORD,
                                   ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
winspool.OpenPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
winspool.ClosePrinter.argtypes = [wintypes.HANDLE]
winspool.StartDocPrinterW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(DOC_INFO_1)]
winspool.EndDocPrinter.argtypes = [wintypes.HANDLE]
winspool.StartPagePrinter.argtypes = [wintypes.HANDLE]
winspool.EndPagePrinter.argtypes = [wintypes.HANDLE]
winspool.WritePrinter.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                  ctypes.POINTER(wintypes.DWORD)]


class PrinterError(Exception):
    pass


def _err(where):
    code = ctypes.get_last_error()
    return PrinterError(f"{where} a échoué (code Windows {code}: {ctypes.FormatError(code).strip()})")


def list_printers():
    """Retourne une liste de dicts {name, port, driver}."""
    flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
    needed, count = wintypes.DWORD(), wintypes.DWORD()
    winspool.EnumPrintersW(flags, None, 2, None, 0, ctypes.byref(needed), ctypes.byref(count))
    if not needed.value:
        return []
    buf = ctypes.create_string_buffer(needed.value)
    if not winspool.EnumPrintersW(flags, None, 2, buf, needed, ctypes.byref(needed), ctypes.byref(count)):
        raise _err("EnumPrinters")
    infos = ctypes.cast(buf, ctypes.POINTER(PRINTER_INFO_2))
    return [{"name": infos[i].pPrinterName, "port": infos[i].pPortName or "",
             "driver": infos[i].pDriverName or ""} for i in range(count.value)]


def send_raw(printer_name: str, data: bytes, doc_name: str = "ServiceTool"):
    """Envoie `data` en mode RAW à l'imprimante. Retourne le nombre d'octets écrits."""
    handle = wintypes.HANDLE()
    if not winspool.OpenPrinterW(printer_name, ctypes.byref(handle), None):
        raise _err("OpenPrinter")
    try:
        doc = DOC_INFO_1(doc_name, None, "RAW")
        if not winspool.StartDocPrinterW(handle, 1, ctypes.byref(doc)):
            raise _err("StartDocPrinter")
        try:
            if not winspool.StartPagePrinter(handle):
                raise _err("StartPagePrinter")
            written = wintypes.DWORD()
            buf = ctypes.create_string_buffer(data, len(data))
            ok = winspool.WritePrinter(handle, buf, len(data), ctypes.byref(written))
            winspool.EndPagePrinter(handle)
            if not ok:
                raise _err("WritePrinter")
            return written.value
        finally:
            winspool.EndDocPrinter(handle)
    finally:
        winspool.ClosePrinter(handle)
