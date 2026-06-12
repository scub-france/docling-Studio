# Contributing

## Getting Started

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/<your-username>/Docling-Studio.git
   cd Docling-Studio
   ```
3. **Create a branch:**
   ```bash
   git checkout -b feature/my-feature
   ```

## Development Setup

Recommended first-time setup:

```bash
bash ./scripts/initial_setup.sh
```

This installs frontend dependencies, syncs the Python dev environments for `document-parser` and `embedding-service`, installs `pre-commit`, and registers the repository hooks.
The commit hooks auto-fix Ruff and frontend formatting issues, then run the `document-parser` architecture tests when backend layers change.
On pull requests, CI enforces `80%` coverage on changed backend lines only.

=== "Backend (Python 3.12+)"

    ```bash
    cd document-parser
    uv sync --group dev

    # Remote mode (lightweight — delegates to Docling Serve)
    uv run uvicorn main:app --reload --port 8000

    # Local mode (full — runs Docling in-process)
    uv sync --group dev --group local
    uv run uvicorn main:app --reload --port 8000
    ```

=== "Frontend (Node 20+)"

    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## Code Quality

### Git hooks

The repository ships with a root `.pre-commit-config.yaml` that auto-fixes Python and frontend files before each commit, runs targeted backend/frontend tests, blocks local/generated artifacts, scans for likely secrets, validates lockfile updates and workflow/compose changes, enforces Conventional Commit messages, runs `document-parser/tests/test_architecture.py` when backend layers change, then runs a frontend type-check, frontend build, and full `document-parser` test suite before each push when those areas changed.

```bash
bash ./scripts/initial_setup.sh

# Or install only the hooks manually
uv tool install pre-commit
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push --hook-type commit-msg
```

### Backend — Ruff

```bash
cd document-parser
uv run ruff check .          # lint
uv run ruff check . --fix    # auto-fix
uv run ruff format .         # format
```

### Backend patch coverage

Pull requests must keep changed backend lines at `>=80%` coverage. The gate is patch-based, so it applies only to lines changed in the PR, not the whole existing backend.

```bash
bash ./scripts/check_backend_patch_coverage.sh origin/main
```

### Frontend — TypeScript + ESLint + Prettier

```bash
cd frontend
npm run type-check          # vue-tsc strict mode
npx eslint src/             # lint
npx prettier --check src/   # check formatting
npx prettier --write src/   # auto-format
```

## Running Tests

=== "Backend"

    ```bash
    cd document-parser
    uv run pytest tests/ -v
    ```

=== "Frontend"

    ```bash
    cd frontend
    npm run test:run
    ```

=== "E2E API (Karate)"

    ```bash
    # Generate test PDFs + start stack
    python e2e/generate-test-data.py
    docker compose up -d --wait

    # Run all API tests
    mvn test -f e2e/api/pom.xml

    # Or by tag: @smoke, @regression, @e2e
    mvn test -f e2e/api/pom.xml -Dkarate.options="--tags @smoke"
    ```

=== "E2E UI (Karate UI)"

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

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Add tests for new functionality
- Update documentation if behavior changes
- Ensure CI passes (lint + type-check + tests + build)

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](https://github.com/scub-france/Docling-Studio/blob/main/LICENSE).
