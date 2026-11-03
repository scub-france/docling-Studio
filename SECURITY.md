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

**Settings** › **Ask** lets a user set the Ollama URL, test it (`POST /api/config/reasoning/test`) and save it. Ask then sends its requests to that URL. The section shows these settings only with `ASK_MODE=visible`, but `ASK_MODE` only hides the screen: the `/api/config/reasoning` routes answer whatever its value. These are outbound requests chosen by the user, so:

- On a HuggingFace deployment (`DEPLOYMENT_MODE=huggingface`), writing the settings and testing the connection are refused with `403`.
- Before connecting, **Test connection** resolves the host and refuses link-local addresses (including the cloud metadata endpoint `169.254.169.254` and `fe80::/10`), multicast, reserved and unspecified addresses. A refused target gets no traffic at all.
- **Save** does not run that check: it only requires an http(s) URL. Anyone who can reach the settings can point Ask at any address the server can reach.
- Loopback and private LAN addresses are allowed on purpose: that is where Ollama usually runs.

## Store connections

An ingestion store (OpenSearch or Neo4j, deprecated and removed in 0.8.0) is created and edited through `/api/stores`, and can carry its own connection URI. The backend connects to that URI to test the store (`POST /api/stores/{slug}/test-connection`) and to push chunks to it. These are outbound connections chosen by the caller, so:

- On a HuggingFace deployment (`DEPLOYMENT_MODE=huggingface`), creating, editing and deleting a store, and removing a document from it, are refused with `403`, and the connection test answers `ok: false` without connecting.
- **Save** (create or edit) resolves the URI's host and refuses the same addresses as the Ollama test: link-local (including `169.254.169.254` and `fe80::/10`), multicast, reserved and unspecified. A refused URI is not saved (`422`).
- **Test connection** runs the same check again before connecting, so a URI saved before the check existed, or whose name now resolves elsewhere, is caught too. A refused target gets no traffic at all.
- A failed test answers with a generic message. The driver's error goes to the server log only, so the test cannot read back what an internal address answers.
- Pushing chunks runs the same check before connecting, and a failed push answers with a generic message too.
- `NEO4J_USER` and `NEO4J_PASSWORD` are sent only to `NEO4J_URI` (same scheme, host and port). A Neo4j store on any other URI must carry its own password, or its test and pushes fail with "credentials required".
- The host is resolved once, before the client connects. A name re-pointed between the two (DNS rebinding) is not caught.
- Loopback and private LAN addresses are allowed on purpose: that is where stores usually run. A store without a URI uses `OPENSEARCH_URL` or `NEO4J_URI`, which only the operator sets.

## Imported Docling documents

`POST /api/analyses/import` accepts a Docling JSON built elsewhere. Two limits bound what one import costs the server:

- The request body is capped at 50 MB on every `/api/analyses` route by the backend, below the bundled nginx's 200 MB (`NGINX_MAX_BODY_SIZE`): an import costs about 44 times its JSON size in memory. A larger body is refused with `413` before it is parsed.
- `MAX_IMPORT_TABLE_CELLS` (default `100000`) caps the grid cells of one document, tables and picture charts together, and a row declared without columns still counts. A document that declares more, or whose cells span more grid positions, is refused with `400`, checked on the raw JSON before the document is validated. `0` lifts the limit.

The app has no login. A self-hosted instance open to untrusted networks must be protected in front of it, for example by a reverse proxy with authentication.
