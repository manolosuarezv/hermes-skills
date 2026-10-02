---
name: hermes-backup-and-update
description: Use when backing up Hermes before an update.
---

# Hermes backup and update

Use this class-level workflow when Manuel asks to back up Hermes, store the backup on a server, and then update Hermes.

## Standing rules

- Back up to the requested remote server before running any update; never treat Hermes' built-in pre-update snapshot as a substitute for the separately requested remote copy.
- Keep Hermes backups strictly separate from Contabilidad and other computing/data backups. Use the dedicated layout `<backup-root>/hermes/ver/` and name each archive with the Hermes version and timestamp, for example `hermes-v0.21.1_YYYYMMDD_HHMMSS.tar.gz`.
- Do not expose credentials, OAuth tokens, `.env` contents, or hashes of secrets in the reply. Keep the archive on the specified server and report only its path, size, and verification status.
- Resolve the active profile through `$HERMES_HOME` when set; default to `~/.hermes` only when it is unset. Do not silently back up another profile.
- Treat a successful `scp`/`rsync` exit as transport success only. Read back the exact remote path and verify size or checksum before proceeding.
- Do not update until remote verification succeeds. If the copy or verification fails, stop and report that Hermes was not updated.

## Procedure

1. Identify the active Hermes home and the remote target. Reuse the user's established SSH key, host, account, and backup root when they are already documented; otherwise ask for the missing server details rather than guessing. Resolve the dedicated Hermes destination before copying; never place the archive in a Contabilidad backup directory.
2. Create a timestamped compressed archive of the active Hermes state and installation data needed for recovery. Exclude caches, bulky transient data, the Contabilidad tree, and unrelated bookkeeping directories unless the user explicitly asks for a full disk image. Preserve configuration and runtime state needed to restore Hermes, but do not print archive contents or secrets.
3. Create `<backup-root>/hermes/ver/` if permissions allow, then transfer the archive there with `scp` or `rsync` over SSH. If the general backup root is root-owned, use the existing user-writable Contabilidad backup parent only as a filesystem parent and create the separate `hermes/ver/` subtree inside it; do not mix files into `backup/`. Use batch/noninteractive SSH options and a bounded connection timeout where available so a dead server does not hang indefinitely.
4. Verify the remote artifact by reading back the exact path over SSH and checking that it exists, is non-empty, and has the expected byte size or SHA-256. Remove any mistakenly placed copy from an unrelated backup directory only after the dedicated copy is verified. Record the remote path and checksum internally for the final report.
5. Only after verification, run the documented updater from an external shell: `hermes update`. The command may update dependencies, migrate configuration, refresh skills, and restart the gateway; obtain the required approval for that side effect.
6. Wait for the updater to exit and require an explicit success result. Do not call a timed-out process a failure if it is still running; wait or poll it to completion.
7. Validate the result with `hermes --version` and the updater's reported commit/version. Confirm the gateway/service restart if the update reports one. Report any non-fatal configuration warnings separately instead of hiding them.
8. If the remote server is powered on or off as part of the workflow, verify the final state independently after the shutdown grace period; never claim it was powered off merely because a poweroff command was issued. If it is still reachable, say so plainly.

## Recovery and reporting

- If the remote backup exists but the update fails, report the verified remote path and stop; do not retry destructive update steps blindly.
- If the update succeeds, report three items only: remote backup path and verification, installed Hermes version/commit, and remaining warnings.
- Prefer concise Spanish responses for Manuel: verdict first, then a short bullet list. Do not replay commands or narrate the investigation.
- When reporting a backup, always show the dedicated remote path and version label; explicitly state whether the server's final power state was verified.

## Reference

- For Hermes update semantics and the optional built-in `--backup` behavior, consult the current official updating documentation before changing the update command.
- For remote macOS gateway lifecycle restrictions, consult `hermes-gateway-ops`; never stop the gateway from inside the running gateway process unless the updater itself performs the managed restart.
