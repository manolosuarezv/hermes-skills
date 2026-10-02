# sshguard & shutdown diagnostics — qbex/server01

## Confirmed behaviour (agosto 2026)

### Shutdown via `systemctl poweroff -f`
- Comando: `sudo -S systemctl poweroff -f` enviado vía expect
- Señal de éxito en cliente SSH: `Connection reset by peer` / `Broken pipe` — el host cortó la red al bajar
- El ICMP puede seguir respondiendo ~15-30 seg después del comando mientras el kernel desmonta el RAID
- Verificación definitiva: `ping -c 4 -t 3 192.168.1.69` → 100% loss = apagado real

### sshguard ban (IP drop, no RST)
- Síntoma: `ping` OK (0% loss) pero `nc -z <IP> 22` silencioso / timeout
- Causa: intentos SSH fallidos rápidos (BatchMode, scripts sin contraseña) activan sshguard
- Distinción vs. shutdown en curso: un ban **persiste** (ping siempre 0%, puerto siempre filtrado); un shutdown en curso **progresa** a 100% loss
- Workaround: esperar >2 min hasta que expire el ban, o pivotar SSH desde otra IP LAN (ThinkPad 192.168.1.117) que no esté baneada

### Pitfall: sudo -S sin tty
- `sudo -S shutdown` sobre SSH con `BatchMode=yes` falla silenciosamente (sudo pide tty, no hay, retorna error pero `|| true` lo swallow)
- **Siempre usar expect** (templates/shutdown.exp) para privilegios — nunca ssh inline con BatchMode

### Secuencia correcta (probada)
1. Escribir script desde `templates/shutdown.exp` a `/tmp/qbex_off.exp` (rellenar PASS inline)
2. `expect /tmp/qbex_off.exp` — esperar "Connection reset by peer"
3. `rm -f /tmp/qbex_off.exp` — borrar inmediatamente
4. `sleep 15 && ping -c 4 -t 3 192.168.1.69` — confirmar 100% loss
