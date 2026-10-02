---
name: agent-interconnectivity
description: Use when connecting agents across hosts. Choose securely.
---

# Agent interconnectivity

Use this workflow when one agent must communicate with another agent or expose selected capabilities across hosts.

## Rules

- Separate transport, protocol, and authorization: Tailscale supplies private reachability; MCP, ACP, or a Hermes peer supplies the application protocol; tokens, profiles, and operation filters supply authorization.
- Identify both runtimes and the desired interaction before configuring anything: agent-to-agent messages, remote tools, or an editor controlling an agent. Do not select MCP or ACP merely because both machines are on Tailscale.
- Prefer `hermes peer` for Hermes-to-Hermes messaging and delegated runs; prefer MCP when one agent needs a narrow, typed tool surface; use ACP when an editor or collaboration host owns the conversation.
- Bind remote services to the remote Tailscale address when supported, otherwise bind narrowly and enforce a host firewall rule; never expose an agent API to the public interface unnecessarily.
- Keep credentials out of chat, source control, command history where possible, and exported transcripts. Store API keys in the owning host's secret environment and verify the authenticated endpoint before sending work.
- Start with read-only or proposal-only capabilities. For accounting or other sensitive domains, the remote agent must not write source books or the canonical store directly; route work through an intake, approval, and audit trail.
- Verify connectivity, identity, authorization, and a harmless read operation separately before enabling mutation or long-running delegation.
- After every external write or remote execution, read back the exact target or job status and retain an auditable identifier.

## Procedure

1. Classify the connection using `references/connection-decision.md`.
2. Inspect both hosts, the actual runtime/profile names, the Tailscale addresses, listening port, and firewall policy. Do not guess the remote Linux user, hostname, or port.
3. Configure the remote service with a strong application credential and the smallest profile/tool set. Keep the credential only in the remote secret store and the client-side secret environment.
4. Establish the private route over Tailscale and test a harmless identity/health request.
5. Register the application connection:
   - Hermes-to-Hermes: `hermes peer add <name> --url <url> --key <key>`, then `hermes peer list` and a short `hermes peer dm` from a file.
   - MCP client: configure the remote HTTP MCP URL, headers, timeout, and explicit tool inclusion; probe tool discovery before calling a tool.
   - ACP host: install the ACP extra if needed and launch `hermes acp`; use stdio or an explicitly managed SSH/host bridge rather than inventing a network ACP endpoint.
6. Test read-only behavior and authorization boundaries. Confirm denied operations remain denied.
7. Enable only the minimum required mutation path, with idempotency keys, approval gates, audit logging, and read-back verification.
8. Document the connection by role and capability, not by copying secrets or recording one-off incident details.

## Hermes-specific notes

Hermes' API server is OpenAI-compatible and can be used by a peer or another frontend. Its default bind is localhost, so remote access requires an intentional bind to a private interface and a configured `API_SERVER_KEY`; use the actual configured port rather than assuming a historical default. The embedded `hermes mcp serve` is stdio-oriented, so a Tailscale MCP deployment needs an HTTP MCP server or a separately managed adapter. ACP is an editor/host integration over stdio, not the default choice for autonomous agent-to-agent messaging.

For the Contabilidad Suárez workflow, expose only intake operations such as listing pending supports, reading a support, proposing a movement, and verifying an artifact. Keep approval, canonical persistence, reconstruction, and derived exports on the controlled accounting host.

See `references/connection-decision.md` for the protocol decision table and secure recipes.

See `references/hermes-agent-inventory.md` for what "agent" means in Hermes and how to list what is alive (sessions, peers, cron, subagents).
