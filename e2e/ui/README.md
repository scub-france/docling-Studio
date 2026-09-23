# E2E UI Tests — Karate UI

Browser-based end-to-end tests for Docling Studio using [Karate UI](https://karatelabs.github.io/karate/karate-core/#ui-automation) (Chrome headless).

## Prerequisites

- **JDK 17+** (e.g. `brew install openjdk@17`)
- **Maven 3.9+** (e.g. `brew install maven`)
- **Google Chrome** (headless, auto-detected)
- **Python 3.12+** (for test data generation)
- **Docker** (for running the full stack)

## Quick start

```bash
# 1. Generate test PDFs (from repo root)
python e2e/generate-test-data.py

# 2. Start the stack
docker compose up -d --wait

# 3. Run all UI tests
mvn test -f e2e/ui/pom.xml

# 4. Tear down
docker compose down
```

## Run by tag

```bash
# Critical only — CI scope (~1min30)
mvn test -f e2e/ui/pom.xml -Dkarate.options="--tags @critical"

# All UI tests — local scope (~3min)
mvn test -f e2e/ui/pom.xml -Dkarate.options="--tags @ui"
```

## Custom URLs

```bash
mvn test -f e2e/ui/pom.xml -DbaseUrl=http://your-host:8000 -DuiBaseUrl=http://your-host:3000
```

## Structure

```
e2e/ui/
├── pom.xml                     # Maven + Karate dependency
├── src/test/java/
│   └── UIRunner.java           # JUnit5 Karate runner
└── src/test/resources/
    ├── karate-config.js        # URLs, timeouts, Chrome driver config
    ├── common/helpers/
    │   ├── upload.feature       # API helper — upload (setup)
    │   ├── analyze.feature      # API helper — analyze (setup)
    │   ├── cleanup.feature      # API helper — delete (teardown)
    │   ├── ui-upload.feature    # UI helper — upload via file input
    │   └── ui-wait-analysis.feature  # UI helper — poll for completion
    ├── documents/               # @critical @ui
    │   ├── upload.feature       # Upload + preview
    │   ├── delete.feature       # Delete via hover + click
    │   └── error-states.feature # Non-PDF rejection, hints
    ├── analyses/                # @critical @ui
    │   ├── analysis.feature     # Run analysis, verify tabs
    │   ├── batch-progress.feature  # Progress bar on multi-page
    │   ├── rechunk.feature      # Prepare mode, rechunk
    │   ├── analysis-detail.feature   # Saved analysis page (@regression)
    │   └── pipeline-options.feature  # OCR, table mode toggles
    ├── navigation/              # @ui
    │   ├── sidebar.feature      # Sidebar navigation
    │   └── i18n.feature         # FR/EN language switch
    └── workflows/               # @ui
        └── full-ui-path.feature # Complete happy path via browser
```

## Tags

| Tag | Scope | When |
|-----|-------|------|
| `@critical` | 5 features, 6 scenarios | CI on `main` branch |
| `@ui` | All UI features | Local development |

## Design patterns

- **Setup via API, verify via UI** — fast setup with API helpers, then browser assertions
- **Cleanup via API** — `cleanup.feature` deletes test data after each scenario
- **Polling with `optional()`** — graceful handling of fast completions (no `waitFor` on spinners that may flash)
- **`data-e2e` selectors** — `[data-e2e=doc-item]` instead of `.doc-item` — decoupled from CSS, never breaks on style refactors
- **`karate.sizeOf()` for counts** — `karate.sizeOf(locateAll('[data-e2e=xxx]'))` instead of raw `.length` or `script()`

## Reports

After a run, Karate HTML reports are in `e2e/ui/target/karate-reports/`.
