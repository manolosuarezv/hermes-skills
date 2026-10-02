#!/usr/bin/env python3
"""
prender-server.py — Envia Wake-on-LAN a la torre qbex (server01) desde el Mac mini.

Uso:
  python3 prender-server.py            # envia WOL a qbex por la LAN
  python3 prender-server.py --check    # hace ping para ver si ya esta prendido

Requiere: la interfaz del server (enp4s0) con WOL habilitado en BIOS/placa.
MAC objetivo: 1c:86:0b:2d:e2:c8  (IP LAN 192.168.1.69)
Tailscale (acceso remoto): 100.119.118.124
"""
import socket
import subprocess
import sys

# Ambas interfaces de qbex: enviamos WOL a las dos para cubrir ambos puertos.
#   enp4s0 = tarjeta gigabit PCIe   -> 1c:86:0b:2d:e2:c8
#   enp0s7 = puerto onboard nForce  -> 44:87:fc:ea:69:da
SERVER_MACS = ["1c:86:0b:2d:e2:c8", "44:87:fc:ea:69:da"]
SERVER_IP = "192.168.1.69"
BROADCAST = "192.168.1.255"
PORT = 9


def send_wol(macs):
    # Magic packet: 6 bytes 0xFF + MAC repetida 16 veces
    for mac in macs:
        mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
        if len(mac_bytes) != 6:
            raise ValueError(f"MAC invalida: {mac}")
        pkt = b"\xff" * 6 + mac_bytes * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(pkt, (BROADCAST, PORT))
        print(f"[OK] Magic packet enviado a {mac} via {BROADCAST}:{PORT}")


def is_up(ip: str) -> bool:
    try:
        r = subprocess.run(
            ["ping", "-c", "1", "-t", "3", ip],
            capture_output=True, timeout=6,
        )
        return r.returncode == 0
    except Exception:
        return False


if __name__ == "__main__":
    if "--check" in sys.argv:
        print(f"qbex ({SERVER_IP}) -> {'ENCENDIDO' if is_up(SERVER_IP) else 'APAGADO/offline'}")
        sys.exit(0)
    print(f"Enviando WOL a qbex (interfaces: {', '.join(SERVER_MACS)})...")
    send_wol(SERVER_MACS)
    print("Espera ~30-60s y verifica con: python3 prender-server.py --check")
