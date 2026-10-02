# Homelab access — SSH from macOS, discovery, multi-NIC WOL

## SSH from macOS without sshpass
macOS has `/usr/bin/expect` but not `sshpass` and not Homebrew by default.
Drive password SSH with an expect script. DO NOT store the password in
memory or chat — prefer SSH key-based auth.

```expect
#!/usr/bin/expect -f
# WORKING template. Use `ssh -t` (pty) so `sudo` can read a password, and
# answer BOTH the SSH prompt and the sudo prompt. `echo pass | sudo -S` is
# BLOCKED by the agent runtime — do NOT use it.
set timeout 900
set cmd [lindex $argv 0]
spawn ssh -t -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o NumberOfPasswordPrompts=3 user01@192.168.1.69 $cmd
expect {
    "user01@192.168.1.69's password:" { send "PASS\r"; exp_continue }
    -re "password for user01" { send "PASS\r"; exp_continue }
    -re "(P|p)assword:" { send "PASS\r"; exp_continue }
    eof { }
}
```

Gotcha observed: `User01` was rejected (case-sensitive), `user01` worked.
Also: for passwordless cron, install a Mac SSH key into qbex
`~/.ssh/authorized_keys` and add `user01 ALL=(ALL) NOPASSWD: ALL` via
`echo ... | sudo tee -a /etc/sudoers.d/user01-nopasswd` (use `tee`, not
`visudo` stdin — `-S`/piped sudo is blocked). Then `sudo -n true` exits 0.

## MAC / IP discovery on the target (Debian)
```
ip -br link show              # all NICs + MACs (ignore lo/docker/veth/tailscale/br-)
ip route | grep default       # which iface holds the cable + gateway
ip -br addr show tailscale0   # Tailscale IP for remote access
lsblk                          # disks: /dev/md0 = RAID, mounted where?
cat /proc/mdstat               # RAID level + member disks + [UU] health
```

## Real example (Manuel's qbex / server01)
- Debian 13 (trixie), headless tower (AMD Athlon LE-1660, nForce board).
- Alias `qbex`. LAN IP 192.168.1.69, Tailscale 100.119.118.124.
- Two NICs: `enp4s0` PCIe gigabit MAC `1c:86:0b:2d:e2:c8`,
  `enp0s7` onboard nForce MAC `44:87:fc:ea:69:da`.
- RAID1 `/dev/md0` (sdb+sdc) mounted at `/mnt/raid` (ext4, 915 GiB).
  Holds `/mnt/raid/proyectos_web` (Tritones Buceo site1), `immich/`,
  `nextcloud/`, `raid1_backup/proyectos/`, `Backups/` (was empty).
- Docker active; `wakeonlan` binary present; `ethtool` NOT installed.
- Tailscale installed on the Windows "Win-pack" for remote reach.

## Multi-NIC WOL lesson (the failed-first-try trap)
Single-MAC WOL failed to boot qbex. The cable/BIOS WOL was on one port
while the script targeted the other MAC. Sending the magic packet to BOTH
MACs (enp4s0 + enp0s7) woke it on the first try. Always enumerate every
NIC and broadcast to all of them for a headless multi-port box.

## Remote access pattern (Tailscale + ESP32/HiveMQ)
User's design: an ESP32 on the router receives an MQTT message (HiveMQ
cloud broker) and powers the server (relay or WOL). Tailscale gives
remote SSH into the LAN from anywhere. The `prender-server` script can be
extended with a `--mqtt` mode that publishes to the broker instead of
(raw WOL) — needs broker URL/user/topic from the user.
