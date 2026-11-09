"""Découverte des imprimantes Canon sur le réseau (protocole BJNP, UDP 8611).

Même mécanisme que les pilotes Canon : une diffusion « discover » à laquelle
chaque imprimante répond avec son adresse MAC et son IP, puis une requête
« get id » qui renvoie l'identifiant IEEE-1284 (modèle, firmware…).
"""
import socket
import struct
import time
from dataclasses import dataclass

BJNP_PORT = 8611


@dataclass
class NetPrinter:
    ip: str
    mac: str
    device_id: str

    def field(self, key):
        for part in self.device_id.split(";"):
            k, _, v = part.partition(":")
            if k.strip().upper() == key:
                return v.strip()
        return ""

    @property
    def model(self):
        return self.field("MDL")

    @property
    def firmware(self):
        return self.field("VER")


def _header(code, seq=0, payload=b""):
    return b"BJNP" + bytes([0x01, code]) + struct.pack(">HHHI", 0, seq, 0, len(payload)) + payload


def _broadcast_addresses():
    addrs = {"255.255.255.255"}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                addrs.add(ip.rsplit(".", 1)[0] + ".255")  # /24 le plus courant
    except OSError:
        pass
    return addrs


def get_device_id(ip, timeout=1.5):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(_header(0x30, 1), (ip, BJNP_PORT))
        r, _ = s.recvfrom(4096)
        return r[18:].decode("latin-1", "replace").strip("\x00") if len(r) > 18 else ""
    except OSError:
        return ""
    finally:
        s.close()


def discover(wait=2.5):
    """Retourne la liste des imprimantes Canon qui répondent sur le réseau local."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.3)
    try:
        for _ in range(2):
            for b in _broadcast_addresses():
                try:
                    s.sendto(_header(0x01), (b, BJNP_PORT))
                except OSError:
                    pass
        replies = {}
        end = time.time() + wait
        while time.time() < end:
            try:
                data, addr = s.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            if data[:4] == b"BJNP" and data[4] == 0x81 and data[5] == 0x01:
                replies[addr[0]] = data
    finally:
        s.close()

    found = []
    for ip, data in replies.items():
        mac = ""
        p = data[16:]
        # charge utile : 00 01 08 00 | lg_mac(6) lg_ip(4) | MAC | IP
        if len(p) >= 6 and p[4] == 6:
            mac = ":".join(f"{b:02x}" for b in p[6:12])
        found.append(NetPrinter(ip, mac, get_device_id(ip)))
    return sorted(found, key=lambda n: tuple(int(x) for x in n.ip.split(".")))
