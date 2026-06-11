# Contributing to Docling Studio

Thank you for your interest in contributing to Docling Studio! This guide will help you get started.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/Docling-Studio.git
   cd Docling-Studio
   ```
3. **Create a branch** for your work:
   ```bash
   git checkout -b feature/my-feature
   ```

## Development Setup

### Docker Dev Stack (recommended)

The fastest way to get the full stack running (backend + frontend + OpenSearch):

```bash
docker compose -f docker-compose.dev.yml up
```

This starts:

| Service | URL | Notes |
|---------|-----|-------|
| Frontend (Vite) | http://localhost:3000 | HMR enabled |
| Backend (FastAPI) | http://localhost:8000 | Auto-reload on file changes |
| OpenSearch | http://localhost:9200 | Single-node, security disabled |
| OpenSearch Dashboards | http://localhost:5601 | Index inspection UI |

Source code is bind-mounted — edits on your host are reflected immediately.

To use remote conversion mode instead of local:

```bash
CONVERSION_MODE=remote docker compose -f docker-compose.dev.yml up
```

### Manual Setup

If you prefer running services directly on your machine:

Recommended first-time bootstrap:

```bash
bash ./scripts/initial_setup.sh
```

This installs frontend dependencies, syncs the Python dev environments for `document-parser` and `embedding-service`, installs `pre-commit`, and registers the repository hooks.
The commit hooks auto-fix Ruff and frontend formatting issues, then run the `document-parser` architecture test suite when backend layers change.
On pull requests, CI enforces `80%` coverage on changed backend lines only.

### Backend (Python 3.12+)

```bash
cd document-parser
uv sync --group dev

# Remote mode (lightweight — delegates to Docling Serve)
uv run uvicorn main:app --reload --port 8000

# Local mode (full — runs Docling in-process)
uv sync --group dev --group local
uv run uvicorn main:app --reload --port 8000
```

### Frontend (Node 20+)

```bash
cd frontend
npm install
npm run dev
```

### Git hooks (recommended)

The repository ships with a root `.pre-commit-config.yaml` that auto-fixes Python and frontend files before each commit, runs targeted backend/frontend tests, blocks local/generated artifacts, scans for likely secrets, enforces Conventional Commit messages, runs `document-parser/tests/test_architecture.py` when backend layers change, then runs a frontend type-check before each push.

```bash
bash ./scripts/initial_setup.sh

# Or install only the hooks manually
uv tool install pre-commit
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push --hook-type commit-msg
```

### Background repo health report

If you want a local `report.json` that refreshes in the background while you work, install the repo health scheduler:

```bash
bash ./scripts/install_repo_health_agent.sh install
```

On macOS this installs a `launchd` job. On Linux it installs a user `systemd` timer. Both call the same shell reporter and write `.repo-health/report.json`. The generator skips a run when `HEAD` and the working tree fingerprint have not changed since the last report.

Useful commands:

```bash
bash ./scripts/install_repo_health_agent.sh status
bash ./scripts/install_repo_health_agent.sh uninstall
```

Portable fallback on any machine with Bash:

```bash
bash ./scripts/run_repo_health_watch.sh 300
```

The generated report is local-only and gitignored. It currently includes:

```text
- document-parser Ruff lint
- document-parser pytest suite
- frontend ESLint
- frontend type-check
- frontend Vitest run
```

## Code Quality

### Backend — Ruff

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting Python code.

```bash
cd document-parser
uv run ruff check .          # lint
uv run ruff check . --fix    # lint with auto-fix
uv run ruff format .         # format
```

### Backend patch coverage

Pull requests must keep changed backend lines at `>=80%` coverage. The gate is patch-based, so it applies only to lines changed in the PR, not the whole legacy codebase.

You can run the same check locally with:

```bash
bash ./scripts/check_backend_patch_coverage.sh origin/main
```

For the embedding service:

```bash
cd embedding-service
uv run ruff check .          # lint
uv run ruff check . --fix    # lint with auto-fix
uv run ruff format .         # format
```

### Frontend — TypeScript + ESLint + Prettier

```bash
cd frontend
npm run type-check          # type check (vue-tsc)
npx eslint src/             # lint
npx prettier --check src/   # check formatting
npx prettier --write src/   # auto-format
```

## Running Tests

```bash
# Backend (377 tests)
cd document-parser
uv run pytest tests/ -v

# Frontend (156 tests)
cd frontend
npm run test:run
```

### E2E API (Karate)

```bash
# Generate test PDFs + start stack
python e2e/generate-test-data.py
docker compose up -d --wait

# Run all API tests
mvn test -f e2e/api/pom.xml

# Or by tag: @smoke, @regression, @e2e
mvn test -f e2e/api/pom.xml -Dkarate.options="--tags @smoke"
```

### E2E UI (Karate UI)

```bash
# Generate test PDFs + start stack (if not already running)
python e2e/generate-test-data.py
docker compose up -d --wait

# Run critical UI tests (CI scope)
mvn test -f e2e/ui/pom.xml -Dkarate.options="--tags @critical"

# Run all UI tests (local scope)
mvn test -f e2e/ui/pom.xml -Dkarate.options="--tags @ui"
```

All tests must pass before submitting a PR.

## Submitting Changes

1. **Commit** with clear, descriptive messages
2. **Push** your branch to your fork
3. Open a **Pull Request** against `main`
4. Describe **what** changed and **why** in the PR description
5. Ensure CI passes (tests + build)

## Branching Strategy

We follow a simplified Git Flow:

| Branch | Purpose |
|--------|---------|
| `main` | Always stable — latest release merged back |
| `release/X.Y.Z` | Release preparation (freeze, bugfixes, changelog) |
| `feature/*` | New features — PR to `main` |
| `fix/*` | Bug fixes — PR to `main` (or `release/*` for pre-release fixes) |
| `hotfix/X.Y.Z` | Urgent fix on a released version — PR to `main` |

Rules:
- All PRs target `main` (never stack branches on other feature branches)
- `release/*` branches are created from `main` when preparing a release
- `hotfix/*` branches are created from the release tag

## Versioning

We use [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

- **Source of truth**: the git tag (`vX.Y.Z`)
- `package.json` version should match the current release branch
- The build injects the version automatically (Vite `__APP_VERSION__` for frontend, `APP_VERSION` env var for backend)

## Release Process

1. **Create the release branch** from `main`:
   ```bash
   git checkout main && git pull
   git checkout -b release/X.Y.Z
   ```

2. **On the release branch**, only:
   - Bug fixes
   - Move `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD` in `CHANGELOG.md`
   - Update `version` in `frontend/package.json`

3. **Merge into `main`** via PR, then **tag on `main`**:
   ```bash
   git checkout main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. The tag triggers the **release workflow** which builds and pushes the Docker image to `ghcr.io`.

### Docker Image Tags

Each release produces two image variants:

| Tag | Description |
|-----|-------------|
| `X.Y.Z-remote` | Exact version — lightweight (Docling Serve) |
| `X.Y.Z-local` | Exact version — full (in-process Docling) |
| `X.Y-remote` | Latest patch of this minor — lightweight |
| `X.Y-local` | Latest patch of this minor — full |
| `latest-remote` | Latest stable — lightweight |
| `latest-local` | Latest stable — full |

### Hotfix

```bash
git checkout vX.Y.Z           # from the release tag
git checkout -b hotfix/X.Y.Z+1
# fix, commit, PR to main
git tag vX.Y.Z+1              # tag on main after merge
```

### Changelog

We follow [Keep a Changelog](https://keepachangelog.com/). Every PR should add a line under `[Unreleased]` in `CHANGELOG.md`. The release branch moves `[Unreleased]` to the versioned section.

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Add tests for new functionality
- Update documentation if behavior changes
- Follow existing code style and conventions

## Reporting Issues

- Use GitHub Issues to report bugs or request features
- Include steps to reproduce for bugs
- Mention your OS, Python/Node version, and Docker version if relevant

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
