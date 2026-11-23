# Security policy

## Supported versions

Only the latest minor version gets security fixes.

| Version | Supported |
|---------|-----------|
| 0.7.x | Yes |
| < 0.7 | No |

## Report a vulnerability

Do not open a public issue.

Report it privately on GitHub: **Security** tab, then **Report a vulnerability** ([direct link](https://github.com/scub-france/Docling-Studio/security/advisories/new)).

Please include:

- what the problem is and how to reproduce it,
- the part affected (`document-parser/`, `frontend/`, the Docker images…),
- what an attacker could do with it,
- a fix idea, if you have one.

## What happens next

| Step | Within |
|------|--------|
| We confirm we received it | 48 hours |
| We assess the severity | 7 days |
| We fix it | 14 days if critical, 30 days otherwise |
| We publish the fix and a GitHub Security Advisory | When the fix is released |

The fix is prepared in the private fork attached to the advisory, so nothing is public before the release. We credit you in the advisory, unless you prefer not.

## For contributors

- Never commit secrets, keys or passwords.
- Validate user input at the API boundary.
- Keep dependencies up to date: in `document-parser/`, `uv pip install pip-audit` then `uv run pip-audit`; in `frontend/`, `npm audit`.

## Reasoning settings and outbound requests

**Settings** › **Reasoning** lets a user set the Ollama URL, test it (`POST /api/config/reasoning/test`) and save it. Ask then sends its requests to that URL. These are outbound requests chosen by the user, so:

- On a HuggingFace deployment (`DEPLOYMENT_MODE=huggingface`), writing the settings and testing the connection are refused with `403`.
- Before connecting, **Test connection** resolves the host and refuses link-local addresses (including the cloud metadata endpoint `169.254.169.254` and `fe80::/10`), multicast, reserved and unspecified addresses. A refused target gets no traffic at all.
- **Save** does not run that check: it only requires an http(s) URL. Anyone who can reach the settings can point Ask at any address the server can reach.
- Loopback and private LAN addresses are allowed on purpose: that is where Ollama usually runs.

The app has no login. A self-hosted instance open to untrusted networks must be protected in front of it, for example by a reverse proxy with authentication.

## DNS rebinding on a local install

With no login, an instance on your own machine relies on the browser keeping other sites away from it. DNS rebinding gets around that: a page you visit points its own domain name at `127.0.0.1` and then calls the API as if it were same-origin. The only trace left is the `Host` header, which still carries the attacker's domain.

- `/mcp` checks `Host` against `MCP_ALLOWED_HOSTS`, on by default.
- `/api` checks it only when `API_ALLOWED_HOSTS` is set; it is off by default so that installs reached by a LAN name or behind a proxy keep working. On a workstation, set `API_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]`. See [Host check on the API](docs/configuration.md#host-check-on-the-api).
- Neither check is access control: a client that is not a browser sets any `Host` it likes.
