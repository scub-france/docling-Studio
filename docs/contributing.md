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

### Backend — Ruff

```bash
cd document-parser
uv run ruff check .          # lint
uv run ruff check . --fix    # auto-fix
uv run ruff format .         # format
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
