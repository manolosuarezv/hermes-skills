# Session notes: hermes doctor vuln remediation (2026-08-25)

## Environment
- Host: macOS, Hermes installed at `~/.hermes`, repo at `~/.hermes/hermes-agent`
- npm 10.9.8, node v22.23.1
- Hermes runtime = Python (`~/.local/bin/hermes` is a bash launcher → Python). npm workspaces are NOT the running runtime.
- Only node processes live: pyright LSP (`scripts/lsp/bin`) and whatsapp-bridge (`scripts/whatsapp-bridge/bridge.js`, port 3000). Web UI not built (`web/dist` absent).

## What `hermes doctor` reported (the visible surface)
- web workspace deps: 0 critical, 7 high, 0 moderate — build-time tooling
- ui-tui workspace deps: 0 critical, 5 high, 0 moderate — build-time tooling

## Actual packages (web workspace, 7 high)
- brace-expansion <=1.1.17 || 4.0.0-5.0.8 (via eslint chains)
- js-yaml 4.0.0-4.3.0 (CVE-2026-59870 not backported)
- nanoid <=3.3.17 (via postcss)
- postcss <=8.5.22 (sourceMappingURL path traversal)
- react-router 7.12.0-7.18.1 (RSC CSRF) → react-router-dom too
- undici 7.0.0-7.28.0 (via jsdom)

## What a ROOT `npm audit` revealed that doctor did NOT (9 more, 1 critical)
- tar <=7.5.20 (CRITICAL — PAX numeric path type confusion + DoS)
- electron 1.3.1-41.10.2 etc. (RSC/iframe bypass; needs --force → electron@40.10.6)
- extract-zip * (symlink path traversal; needs --force)
- dompurify <=3.4.12 (moderate XSS)
- fast-uri 3.0.0-3.1.4 (host confusion)
- mermaid 11.0.0-alpha.1-11.16.0 (moderate, prototype pollution / DoS)
- shell-quote <=1.8.4 (DoS; via concurrently)
(all in apps/desktop + root devDeps)

## Actions taken (safe, no --force)
1. `cp package-lock.json /tmp/hermes-package-lock.backup.json`
2. `npm audit fix --dry-run` (confirmed no package.json edits)
3. `npm audit fix --workspace web`  → web 7 → 2 high (react-router stuck at 7.18.0)
4. `npm audit fix --workspace ui-tui` → ui-tui 5 → 0 high
5. `npm install react-router-dom@^7.18.2 --workspace web` → web 2 → 0 high
6. `npm install react-router-dom@^7.18.2 --workspace apps/desktop` → desktop 7.18.0 → 7.18.2
7. `npm audit fix` (root, in-range) → 9 → 4 high (electron/extract-zip remain, --force only)

## Result
- doctor's web + ui-tui: 0 high ✓
- root npm audit non-force items: gone
- Left intentionally: electron + extract-zip (require `--force` → out-of-range electron@40.10.6, breaks desktop build). Not reported by doctor.

## Key lesson
`hermes doctor` UNDER-REPORTS npm vulns — it only scans web/ui-tui. Always run a root `npm audit` to see the real count before declaring "fixed", and never `--force` electron in this repo.
