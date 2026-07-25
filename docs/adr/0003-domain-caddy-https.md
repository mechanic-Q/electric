# ADR 0003: Domain + Caddy + HTTPS on Hong Kong Showcase Server

## Status

Accepted

## Context

ADR 0001 established the Hong Kong Showcase Server and stated "Use IP-based launch first. Add domain and HTTPS later after the server is reachable." The server has been running on `8.210.117.245:8000` since initial deployment. A domain `el-forecast.asia` has been acquired with DNS managed at Alibaba Cloud.

The server currently serves the Showcase WebUI via uvicorn directly on `0.0.0.0:8000` — no TLS, no domain name, no reverse proxy. The server is an Aliyun ECS (Ubuntu 22.04, 2 vCPU, 2 GB RAM) running `ellectric.service` under systemd.

For a public showcase, visitors expect:
- A domain name (`el-forecast.asia`) instead of a raw IP:port
- HTTPS (TLS) without browser security warnings
- Automatic certificate renewal

## Decision

Serve the Showcase WebUI on `el-forecast.asia` over HTTPS using Caddy as a reverse proxy in front of the existing FastAPI/uvicorn application.

### Specifics

- **Caddy** as the reverse proxy and TLS terminator (simpler than nginx; auto-provisions and renews Let's Encrypt certificates with no manual configuration).
- **Apex primary**: `el-forecast.asia` is the canonical domain. `www.el-forecast.asia` issues a 301 redirect to the apex.
- **Reverse-proxy**: Caddy forwards requests to `127.0.0.1:8000` (not `0.0.0.0:8000` — uvicorn is bound to localhost only, so the application is not directly exposed to the internet).
- **Certificate**: Let's Encrypt via Caddy's automatic HTTPS. No manual renewal steps.
- **systemd**: Caddy runs as its own systemd unit (`caddy.service`). The existing `ellectric.service` is preserved and unchanged in its function; only the `--host` flag changed from `0.0.0.0` to `127.0.0.1`.

### DNS

The owner must:
1. Add A records at Alibaba Cloud DNS: `@` and `www` → `8.210.117.245`.
2. Open inbound ports 80 and 443 in the Aliyun security group (the OS-level `ufw` is inactive; all inbound filtering is at the cloud security-group layer).

### What does NOT change

- The `ellectric.service` WorkingDirectory, environment variables, and rest of the ExecStart command stay unchanged.
- The deployment flow: `git push` → server `git pull` → `npm run build` → `systemctl restart ellectric` stays the same. After domain setup, additionally `systemctl restart caddy` may be needed if the Caddy config changes.
- The application code (FastAPI, WebUI, Copilot) is not modified.

## Consequences

Positive:

- Visitors reach the site over HTTPS on a clean domain name. No browser warnings.
- Caddy handles certificate lifecycle automatically.
- uvicorn is no longer exposed to the internet — one less attack surface.
- Caddy is simpler to configure than nginx for this use case.

Negative:

- Caddy adds one more moving part to the server (another service to monitor).
- If `el-forecast.asia` needs to move to a different provider later, the Caddy configuration must be updated.
- The owner must manage DNS records and cloud security group at Alibaba Cloud — these are not controlled from the server.

## Alternatives Considered

### nginx

Rejected for this scope. Caddy's automatic HTTPS removes the certbot/certificate-renewal plumbing nginx requires. For a single-site reverse-proxy with TLS, Caddy is the simpler choice. nginx would be preferred if multiple virtual hosts or complex rewrite rules were needed.

### Keep direct uvicorn on port 443 with certbot

Rejected. uvicorn is not designed to run as a TLS-terminating reverse proxy. Running certbot to provision certificates for a uvicorn socket would be more complex than using Caddy.

### Cloudflare Tunnel

Rejected — would add an external dependency and a DNS change at Cloudflare. The server is already reachable; a direct Caddy reverse-proxy is the simplest path to HTTPS.

## Follow-Up Work

- After DNS records propagate and the security group is opened, enable and start caddy: `systemctl enable --now caddy`.
- Verify: `curl -I https://el-forecast.asia` returns 200, `curl -I https://www.el-forecast.asia` returns 301.
- Verify: `curl http://8.210.117.245:8000` times out or connection refused (port 8000 not exposed to the internet).
- The `DEEPSEEK_API_KEY` remains in plaintext in `ellectric.service`. Consider moving it to `/etc/ellectric.env` as a follow-up improvement.
