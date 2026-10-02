#!/usr/bin/env python3
"""
wol.py — Wake-on-LAN magic-packet sender (pure Python, no wakeonlan binary).

Usage:
  python3 wol.py MAC1 [MAC2 ...]          # send to given MAC(s)
  python3 wol.py                          # send to SERVER_MACS below
  python3 wol.py --check 192.168.1.69     # ping to see if host is up

Uses the LAN broadcast address; set BROADCAST/PORT to match the subnet.
Multi-NIC note: pass BOTH MACs of a server so WOL fires regardless of
which port the cable / BIOS WOL is on.
"""
import socket
import subprocess
import sys

# Default targets for a specific homelab tower (override via argv).
# qbex/server01: enp4s0 = PCIe gigabit, enp0s7 = onboard nForce.
SERVER_MACS = ["1c:86:0b:2d:e2:c8", "44:87:fc:ea:69:da"]
BROADCAST = "192.168.1.255"
PORT = 9


def send_wol(macs):
    for mac in macs:
        b = bytes.fromhex(mac.replace(":", "").replace("-", ""))
        if len(b) != 6:
            raise ValueError(f"MAC invalida: {mac}")
        pkt = b"\xff" * 6 + b * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(pkt, (BROADCAST, PORT))
        print(f"[OK] Magic packet -> {mac} via {BROADCAST}:{PORT}")


def is_up(ip):
    try:
        r = subprocess.run(["ping", "-c", "1", "-t", "3", ip],
                           capture_output=True, timeout=6)
        return r.returncode == 0
    except Exception:
        return False


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--check" in sys.argv:
        ip = args[0] if args else "192.168.1.69"
        print(f"{ip} -> {'ENCENDIDO' if is_up(ip) else 'APAGADO/offline'}")
        sys.exit(0)
    macs = args if args else SERVER_MACS
    print(f"Enviando WOL ({', '.join(macs)})...")
    send_wol(macs)
    print("Espera 45-60s y verifica: python3 wol.py --check <ip>")
