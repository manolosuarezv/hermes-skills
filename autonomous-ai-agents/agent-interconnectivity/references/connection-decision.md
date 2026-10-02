# Agent connection decision table

| Need | Preferred path | Why | Boundary |
| --- | --- | --- | --- |
| Hermes agent sends a task or DM to another Hermes agent | `hermes peer` over Tailscale | Native cross-machine Bot Chat and peer roster | Remote API key plus named profile |
| Agent consumes narrow remote operations | HTTP MCP over Tailscale | Typed tool discovery and per-tool filtering | Include only approved tools; use bearer token or mTLS |
| IDE/editor drives Hermes | ACP over stdio | ACP hosts own the conversation and render approvals/tool activity | Run `hermes acp` under the intended OS account |
| Generic frontend calls an agent | Hermes API server over Tailscale | OpenAI-compatible HTTP interface | Strong `API_SERVER_KEY`, private bind, explicit profiles |

## Hermes-to-Hermes recipe

On the remote host, enable the API server in its secret environment and choose a private bind and explicit port:

```bash
API_SERVER_ENABLED=true
API_SERVER_HOST=<remote-tailscale-ip>
API_SERVER_PORT=<chosen-port>
API_SERVER_KEY=<strong-secret>
hermes gateway
```

On the client host:

```bash
hermes peer add <peer-name> --url http://<remote-tailscale-ip>:<chosen-port> --key <secret>
hermes peer list
hermes peer dm <peer-name> < request.txt
hermes peer status <peer-name> <run-id>
```

Do not paste the key into a transcript. Prefer a secret environment or password manager; use a file for the message body so shell interpolation cannot alter the request.

## MCP recipe

The remote service must expose an HTTP MCP endpoint. Configure the client with its URL, authentication header, timeout, and an allowlist of tools. Probe discovery, then call a harmless read tool. Do not assume `hermes mcp serve` is an HTTP listener: the embedded Hermes server is stdio-oriented and needs a separately managed HTTP adapter for a Tailscale deployment.

## ACP recipe

Install the ACP extra from the Hermes checkout when required, then verify:

```bash
hermes acp --check
hermes acp
```

A host such as VS Code or Zed launches and owns the stdio process. Use ACP for host/editor integration, not as a substitute for a peer protocol. If an SSH bridge is used, authenticate the OS connection separately and verify the remote process identity.

## Verification checklist

- Tailscale route reaches the intended host and no public interface is exposed.
- The service identifies the expected host/profile.
- Authentication fails with an invalid credential.
- Read-only discovery succeeds.
- A forbidden write is rejected.
- An approved test write, if needed, has an idempotency key and is read back exactly.
- Logs identify caller, target profile, operation, result, and correlation/run ID without logging secrets.
