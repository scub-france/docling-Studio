# Onboarding Guide — First Contribution

Welcome! This guide helps you go from zero to your first merged PR.

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.12+ | `python --version` |
| Node.js | 20+ | `node --version` |
| Docker & Docker Compose | latest | `docker compose version` |
| Git | 2.x | `git --version` |
| Java (for e2e) | 17+ | `java --version` |
| Maven (for e2e) | 3.9+ | `mvn --version` |

## Step 1 — Fork & Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/<your-username>/Docling-Studio.git
cd Docling-Studio
git remote add upstream https://github.com/scub-france/Docling-Studio.git
```

## Step 2 — Run the Stack

The fastest way to see the app running:

```bash
docker compose up -d --wait
open http://localhost:3000
```

## Step 3 — Set Up for Development

### Backend

```bash
cd document-parser
uv sync --group dev
uv run uvicorn main:app --reload --port 8000  # remote mode (lightweight)
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

## Step 4 — Pick Your First Issue

Look for issues labeled:

- `good-first-issue` — small, well-scoped, mentored
- `help-wanted` — we need help but it may be larger
- `docs` — documentation improvements (great starting point)

## Step 5 — Create a Branch

```bash
git checkout main && git pull upstream main
git checkout -b feature/my-change    # or fix/my-fix
```

Follow the [branching strategy](https://github.com/scub-france/Docling-Studio/blob/main/CONTRIBUTING.md#branching-strategy).

## Step 6 — Code

- Read the [architecture docs](../architecture.md) to understand the codebase
- Follow the [coding standards](../architecture/coding-standards.md)
- Write tests for your changes

## Step 7 — Verify

```bash
# Backend
cd document-parser
uv run ruff check . && uv run ruff format --check .
uv run pytest tests/ -v

# Frontend
cd frontend
npm run type-check
npx eslint src/
npm run test:run
```

## Step 8 — Commit & Push

Follow [commit conventions](../git-workflow/commit-conventions.md):

```bash
git add <files>
git commit -m "feat(scope): short description"
git push origin feature/my-change
```

## Step 9 — Open a PR

- Target: `main` (or `release/*` for pre-release fixes)
- Fill in the [PR template](https://github.com/scub-france/Docling-Studio/blob/main/.github/PULL_REQUEST_TEMPLATE.md)
- Add a line in `CHANGELOG.md` under `[Unreleased]`
- Wait for CI to pass, then request a review

## What to Expect

- A maintainer will review your PR within **3 business days**
- You may get feedback — this is normal and helpful
- Once approved, a maintainer will merge your PR
- Your contribution appears in the next release's changelog

## Need Help?

- Open a [Discussion](https://github.com/scub-france/Docling-Studio/discussions) on GitHub
- Check existing issues for similar questions
- Read the [CONTRIBUTING guide](https://github.com/scub-france/Docling-Studio/blob/main/CONTRIBUTING.md) for detailed rules
