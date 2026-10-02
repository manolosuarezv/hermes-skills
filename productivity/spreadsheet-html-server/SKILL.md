---
name: spreadsheet-html-server
description: Use when serving Excel as searchable HTML.
version: 1.0.0
category: productivity
---

# Spreadsheet HTML server

Use this workflow when the user wants to inspect `.xlsx` accounting or investment workbooks in a browser, especially from another device on the same LAN or Tailscale network.

## Procedure

1. Identify the intended workbook before starting anything. If an attachment path is incomplete or unavailable, inspect the project’s known accounting directory and choose the explicitly current source, not a backup, archive, or similarly named family/individual book. Inventory every candidate’s sheet names and dimensions with `openpyxl`; do not assume monthly ledgers and portfolio sheets share a layout.
2. Inspect any existing viewer and listener before creating a second one: read the server script, check `lsof -nP -iTCP:<port> -sTCP:LISTEN`, and reuse a healthy process when it already serves the requested data. This prevents port collisions and avoids claiming a newly started process when none was started.
3. Build or repair a read-only viewer with Python stdlib `http.server` and `openpyxl`. Read workbooks on each request so later workbook edits appear without regenerating HTML. Preserve Unicode sheet names, dates/times, formulas as source data when needed, and cached results only for display. Add sheet navigation and free-text search when the viewer is meant for interactive inspection; render each sheet according to its actual header structure and support auxiliary investment/portfolio sheets.
4. Discover the serving host’s private addresses before choosing the URL. Use the LAN address when the client is on that LAN and the Tailscale address for remote access. Bind to the selected private interface when practical; if an existing trusted service binds `0.0.0.0`, do not rewrite it merely for this inspection, but report the exposure accurately and avoid forwarding it publicly.
5. Verify the exact service, not just the script: request `http://127.0.0.1:<port>/` and each advertised private URL with `urllib` or `curl`; require HTTP 200, HTML content, and recognizable workbook names/sheet names/data. Confirm the listener with `lsof` and report whether the process must remain running. Give the browser URL plainly.

## Rules and pitfalls

- Keep the viewer read-only and never save a workbook loaded with `data_only=True`; saving that view can replace formulas with cached values.
- Load `data_only=True` for displayed formula results and `data_only=False` when source formulas must be preserved or inspected; `openpyxl` does not calculate formulas.
- Treat a loopback HTTP 200 as insufficient for another-device access: test the actual LAN or Tailscale address advertised to the user.
- Do not hard-code an interface address from an old script or print unreachable fallback URLs; derive advertised URLs from current interface discovery and the client’s network.
- Use the workbook’s real path and preserve the original; the viewer must not edit, regenerate, or overwrite the source workbook.
- For financial data, prefer a specific private bind; if legacy code uses `0.0.0.0`, disclose that it is all-interface exposure and consider narrowing it in a deliberate maintenance change.
- Report the exact start command only when you started the process; otherwise say that an existing listener was verified.
