# OrbStack + external exFAT volume: stale virtiofs cache → EBADF

## Symptom
A container bind-mounting a path on an external exFAT volume fails inside it:

```
EBADF: bad file descriptor, open '/data/encoded-video/.immich'
EBADF: bad file descriptor, scandir '/data/backups'
ls: cannot open directory '/data/backups': Bad file descriptor
```

but the exact same paths read fine from macOS (`ls`, `cat`). Only SOME subdirs
fail; sibling dirs are fine. The container's listing shows entries the host no
longer has — a frozen snapshot of the tree at some past moment.

## Why it looks like an app bug (it is not)
A long-running container passed its mount check at startup and kept serving, so
nothing noticed the cache going stale. **Recreating the container re-runs the
check against the broken cache**, which fails and — under `restart: always` —
becomes a restart loop. Upgrading the app is therefore the classic way to
discover this. Immich's shape of it:

```
[StorageService] Verifying system mount folder checks, current state:
  {"mountChecks":{"thumbs":true,"upload":true,"backups":true,...}}
[StorageService] ERROR Failed to read (/data/encoded-video/.immich): EBADF
microservices worker error: Failed to read: "<UPLOAD_LOCATION>/encoded-video/.immich"
microservices worker exited with code 1
Killing api process
```

Note the mount check reports `true` for the failing folders — it only lists them;
the read of the `.immich` marker is what actually trips.

## Root cause
OrbStack's virtiofs share cache went stale (macOS 27 mounts exFAT via the new
`fskit` driver — `com.apple.fskit.exfat`). The cache did not invalidate when the
volume was remounted/reformatted under a running OrbStack.

## Confirm it in ~10 seconds (do NOT test with the app)
```sh
docker run --rm -v /Volumes/<disk>/<path>:/data:ro alpine sh -c \
  'for d in a b c; do printf "%-12s " "$d:"; ls /data/$d >/dev/null 2>&1 && echo OK || echo FALLA; done'
```
Same failure on a clean `alpine` image = mount layer, not the app. Prove the
host is fine at the same time: `cat /Volumes/<disk>/<path>/<sub>/.immich`.

Remounting the SAME path into a different container does NOT help — the stale
cache is keyed to the share, not the mount point.

## Fix, cheapest first
1. `diskutil unmount /Volumes/<disk> && diskutil mount /dev/<diskXsY>`
   (no sudo needed on this Mac) — **usually NOT enough**.
2. `orbctl stop && orbctl start` — **this is the one that clears it.**
   Downside: every Docker container on the host stops and restarts.
   `orbctl status` should report `Stopped` then `Running`.
3. Reboot the Mac Mini.

Then re-run the throwaway-container check. Only when every subdir is OK and
`cat /data/<sub>/.immich` returns the marker, bring the app back up.

## Prevention
- Keep container app-data (DB, config) on the internal APFS disk. Bind-mount
  exFAT only for bulk media that you rarely remount.
- Never `lsof +D /Volumes/<disk>` — it hangs on large exFAT trees.
- After any remount/reformat of the external volume, restart OrbStack before
  recreating containers that mount it.
