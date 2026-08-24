# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | Yes       |
| < 0.3   | No        |

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please report them privately:

1. **Email**: Send a detailed report to **[INSERT SECURITY EMAIL]**
2. **GitHub Security Advisory**: Use [GitHub's private vulnerability reporting](https://github.com/scub-france/Docling-Studio/security/advisories/new)

### What to include

- Description of the vulnerability
- Steps to reproduce
- Affected component(s): `document-parser/`, `frontend/`, `docker-compose.yml`, etc.
- Impact assessment (data exposure, denial of service, privilege escalation, etc.)
- Suggested fix (if any)

### Response timeline

| Step | SLA |
|------|-----|
| Acknowledgment | < 48 hours |
| Initial assessment | < 7 days |
| Fix developed | < 14 days (critical), < 30 days (other) |
| Public disclosure | After fix is released |

### Process

1. We acknowledge your report and assign a severity level
2. We develop a fix in a **private branch** (never pushed publicly before the advisory)
3. We release the fix and publish a GitHub Security Advisory
4. We credit the reporter (unless they prefer anonymity)

## Security Best Practices (for contributors)

- Never commit secrets, API keys, or credentials
- Never disable CORS or security middleware without review
- Validate all user input at the API boundary
- Keep dependencies up to date (`pip audit`, `npm audit`)
- Follow the [OWASP Top 10](https://owasp.org/www-project-top-ten/) guidelines

## Runtime reasoning config & SSRF

The reasoning configuration can be edited at runtime from the admin panel
(`/settings`), which lets a user set the Ollama host URL and probe it via
`POST /api/config/reasoning/test`. This is a user-supplied outbound request,
so the trust model is:

- **HuggingFace deployment (public surface)**: config writes and the
  connection probe are refused with `403`. The reasoning config is read-only
  there — the public endpoint never issues an outbound request on behalf of a
  visitor.
- **SSRF guard on the probe**: before any request, the probe resolves the
  target hostname and refuses addresses that are never a legitimate Ollama —
  link-local (including the cloud metadata endpoint `169.254.169.254` and
  `fe80::/10`), multicast, reserved, and unspecified (`0.0.0.0`, `::`). Blocked
  targets produce no network traffic at all.
- **Loopback / LAN are allowed on purpose**: the legitimate target — an Ollama
  daemon — runs on loopback or the private LAN by default
  (`http://localhost:11434`). Blocking loopback / RFC1918 would break the
  normal feature, so those ranges are intentionally permitted.
- **Self-hosted exposure is a deployment responsibility**: because loopback and
  the LAN are reachable by design, a self-hosted instance exposed to untrusted
  networks must be protected at the network layer (e.g. an authenticated
  reverse-proxy in front of the parser). The application-level guard only stops
  metadata / link-local / reserved targets, not access to your own LAN.
