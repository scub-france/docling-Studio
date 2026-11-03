# Maintainers

## Release a version

```mermaid
flowchart LR
    Freeze("Freeze commit<br/>on release/x.y.z") --> PR("Pull request<br/>to main")
    PR -->|release gate<br/>says GO| Merge("Rebase<br/>and merge")
    Merge --> Tag("Tag<br/>vX.Y.Z")
    Tag --> Images("Images pushed<br/>to ghcr.io")
    Images --> Deploy(["GitHub Release,<br/>then deploy"])

    classDef orange fill:#FF57221F,stroke:#FF5722,stroke-width:2px
    classDef teal fill:#0096881F,stroke:#009688,stroke-width:1.5px
    classDef green fill:#43A0471F,stroke:#43A047,stroke-width:1.5px
    class Freeze,PR,Merge orange
    class Tag,Images teal
    class Deploy green
```

1. **Audit.** Run the [quality audit](audit/master.md) on the release branch and fix what blocks.
2. **Freeze.** On `release/x.y.z`, make one commit `chore(release): freeze [x.y.z]` that:
    - renames `[Unreleased]` to `[x.y.z] - YYYY-MM-DD` in `CHANGELOG.md`, and adds a new, empty `## [Unreleased]` above it for the next changes,
    - sets the version in `frontend/package.json` and `frontend/package-lock.json`, with `cd frontend && npm version x.y.z --no-git-tag-version`.
3. **Pull request.** Open `release/x.y.z` → `main`. The release gate runs and posts GO, GO CONDITIONAL or NO-GO as a comment. `main` needs one approval.
4. **Merge** with **Rebase and merge**.
5. **Tag** `main`:

    ```bash
    git checkout main
    git pull
    git tag vX.Y.Z
    git push origin vX.Y.Z
    ```

6. **Images.** The tag starts `release.yml`. It builds the `local` and `remote` images for amd64 and arm64 and pushes `X.Y.Z-*`, `X.Y-*` and `latest-*` to `ghcr.io/scub-france/docling-studio`. The `local` image includes the Ask packages.
7. **GitHub Release.** The workflow does not create it. Create it from the tag, with the version's section of `CHANGELOG.md` as notes:

    ```bash
    awk '/^## \[X.Y.Z\]/{f=1; next} /^## \[/{f=0} f' CHANGELOG.md > notes.md
    gh release create vX.Y.Z --title vX.Y.Z --notes-file notes.md
    ```

8. **Deploy** with the [deployment checklist](release/deployment-checklist.md).
9. **Next version.** Create the next release branch from `main`, and its milestone on GitHub:

    ```bash
    git checkout -b release/X.Y.Z main
    git push -u origin release/X.Y.Z
    ```

## What the release gate checks

It runs on every pull request to `main` and posts a verdict: GO, GO CONDITIONAL (only the dependency audit or the audit script failed), or NO-GO.

| Check | What it runs |
|-------|--------------|
| Lint and type-check | Ruff, ESLint, vue-tsc |
| Unit tests | pytest, Vitest |
| Dependency audit | pip-audit on every Python group the images ship (including `local` and `reasoning`), npm audit. Only a critical npm finding fails it. |
| Audit script | `profiles/fastapi-vue/commands.sh` |
| Docker build | Both images, amd64. `local` includes the Ask packages, as published, but not the models. |
| Smoke test | The remote image answers `/api/health`. The local image starts with no network, and `/api/health` reports `engine: local` and `reasoningAvailable: true`. |
| Image scan | Trivy on both images. Critical findings block. |
| Image size | The remote image, compared with the previous release. Warning only. |
| End-to-end | API (`@smoke`, `@regression`, `@e2e`) and UI (`@critical`) |

Known gaps in the workflow today:

- The audit script is not in the repository, so its check passes without checking anything.
- The Python audit never reports anything as critical.
- The gate builds neither the models of the `local` image nor the arm64 images. They are first built when the tag starts `release.yml`.
- `Docker smoke test — local` counts in the gate's verdict, but it is not a required check on `main` until an administrator adds it to the branch protection.
- The UI end-to-end tests outside `@critical` run in no workflow. Run them by hand with `UIRunner#testLocal` (see `e2e/ui/README.md`).

## Hotfix

1. Branch `hotfix/<issue>-<slug>` from `main`.
2. Fix, add a test, open a pull request to `main`, squash it.
3. Tag the next patch version on `main`, for example `v1.2.4` after `v1.2.3`: the images follow.
4. Make sure the fix also lands in the open release branch.

## Checklists and references

| Topic | Page |
|-------|------|
| Merging pull requests | [Merge policy](git-workflow/merge-policy.md) |
| Commit messages | [Commit conventions](git-workflow/commit-conventions.md) |
| Reviewing | [Code review checklist](git-workflow/code-review-checklist.md) |
| Coding rules | [Coding standards](architecture/coding-standards.md) |
| Architecture decisions | [ADR guide](architecture/adr-guide.md) |
| Deploying, rolling back | [Deployment checklist](release/deployment-checklist.md), [Rollback playbook](release/rollback-playbook.md) |
| Incidents, security, monitoring | [Incident response](operations/incident-response.md), [Security response](operations/security-response.md), [Monitoring](operations/monitoring-checklist.md) |
| Triaging issues | [Issue triage](community/issue-triage-process.md) |
| Quality audit | [Audit master](audit/master.md) and its 12 checklists |
| Downloads from HuggingFace | [HuggingFace dependency map](architecture/huggingface-dependency-map.md) |
