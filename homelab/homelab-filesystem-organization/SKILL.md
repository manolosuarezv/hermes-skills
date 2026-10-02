---
name: homelab-filesystem-organization
description: "Use when reorganizing folders on a homelab server."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [homelab, server, ssh, filesystem, folders, merge, organization]
---

# Homelab Filesystem Organization

Use this skill when the user asks to rename, merge, move, or clean up folders on a remote homelab server.

## Procedure

1. Identify the target server and exact root scope before changing anything. For server01/qbex, connect as `user01@192.168.1.69` with the configured SSH key and operate only under the requested root.
2. Discover candidate directories with bounded `find`, not an unbounded traversal. Inspect names, sizes, permissions, and immediate contents:
   ```sh
   find /mnt/raid -mindepth 1 -maxdepth 3 -type d -printf '%p\n' | sort
   du -sh /mnt/raid/<candidate> 2>/dev/null
   find /mnt/raid/<candidate> -mindepth 1 -maxdepth 2 -printf '%y %P\n' | sort
   ```
3. Before merging, compare relative paths in source and destination. Stop if any relative path collides; do not overwrite silently. A short Python `pathlib` comparison is suitable when `rsync` is unavailable.
4. For a clean, non-conflicting merge, move the source's immediate children into the canonical destination, remove the now-empty source directory, and verify both the destination contents and source absence. Prefer `mv` for a same-filesystem move because it preserves data and is fast.
5. Report the canonical path, what was merged, total size, conflicts (if any), and confirmation that the old path no longer exists.

## Naming and separation rules

- Use the user's requested canonical spelling exactly; do not normalize case casually. On this server, `Documentos` and `documentos` are distinct paths.
- Keep independent domains separated: Hermes backups belong under `/mnt/raid/backups/hermes/ver/`; Contabilidad belongs under `/mnt/raid/backups/contabilidad_suarez/`; documents belong under `/mnt/raid/Documentos`.
- Do not merge a directory merely because its name is similar. First inspect its contents and ownership/domain; names such as `documents` inside a Hermes backup are internal Hermes data, not server-level documents.
- Never delete a source directory before verifying that its children were moved and the destination is readable.
- Do not use recursive deletion as a substitute for merging. If cleanup is required, remove only a verified empty source or an explicitly approved staging copy.

## Pitfalls

- Check case-sensitive duplicates before merging because Linux treats `Documentos` and `documentos` as different directories.
- Do not rely on `rsync` being installed on a minimal server; use a collision check plus `mv`, or a Python file comparison, when it is absent.
- Do not search the entire RAID recursively with a long-running command when a bounded inspection of likely roots answers the question; large application trees can cause timeouts.
- Treat a successful SSH command as insufficient evidence: verify the final tree, destination size, and source absence after every move.
