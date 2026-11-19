"""Hexagonal architecture tests — enforce layer dependency rules.

Uses AST import scanning for layer and third-party dependency constraints.
Existing layer violations are listed exactly, so new ones fail the suite.

Rules enforced:
- domain   -> no import from api, services, infra, persistence
- services -> no import from api, infra, persistence
- api      -> no import from infra, persistence
- infra    -> no import from api, services
- mcp_adapter -> no import from api, infra, persistence
- persistence -> no import from api, services, infra
- domain   -> no import of fastapi, sqlalchemy, httpx, opensearchpy
- services -> no import of API or infrastructure adapter packages
- services -> no filesystem access (`os`, `shutil`, `pathlib.Path`, `open()`)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import ClassVar

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SKIP_PATH_PARTS = {"__pycache__", ".venv", ".ruff_cache", "uploads", "data"}

# ---------------------------------------------------------------------------
# Helper: collect top-level imports from all .py files in a package
# ---------------------------------------------------------------------------


def _collect_imports(package: str) -> set[str]:
    """Return the set of top-level module names imported by *package*."""
    pkg_path = Path(_PROJECT_ROOT) / package
    imports: set[str] = set()
    for py_file in pkg_path.rglob("*.py"):
        if any(part in _SKIP_PATH_PARTS for part in py_file.parts):
            continue
        tree = ast.parse(py_file.read_text(), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
    return imports


# ---------------------------------------------------------------------------
# Inter-layer dependency rules (AST; import targets resolve as written)
# ---------------------------------------------------------------------------

_LAYER_RULES = {
    "domain": {"api", "services", "infra", "persistence"},
    "services": {"api", "infra", "persistence"},
    "api": {"infra", "persistence"},
    "infra": {"api", "services"},
    "mcp_adapter": {"api", "infra", "persistence"},
    "persistence": {"api", "services", "infra"},
}

# Pre-existing violations, recorded as exact source and target modules. They
# remain migration debt; a new import or a different target cannot use this list.
_LEGACY_LAYER_IMPORTS = {
    ("persistence/store_repo.py", "infra.secrets"),
}


def _import_targets(tree: ast.AST) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _layer_violations(layer: str) -> set[tuple[str, str]]:
    violations: set[tuple[str, str]] = set()
    for py_file in (_PROJECT_ROOT / layer).rglob("*.py"):
        if any(part in _SKIP_PATH_PARTS for part in py_file.parts):
            continue
        source = str(py_file.relative_to(_PROJECT_ROOT))
        for target in _import_targets(ast.parse(py_file.read_text(), filename=source)):
            if target.split(".")[0] in _LAYER_RULES[layer]:
                violations.add((source, target))
    return violations


@pytest.mark.parametrize("layer", sorted(_LAYER_RULES))
def test_layer_imports(layer: str):
    unexpected = _layer_violations(layer) - _LEGACY_LAYER_IMPORTS
    assert not unexpected, f"New forbidden layer imports: {sorted(unexpected)}"


def test_layer_scanner_detects_a_forbidden_import(tmp_path, monkeypatch):
    """Guard against a green suite when the import graph is not resolved."""
    source = tmp_path / "api" / "probe.py"
    source.parent.mkdir()
    source.write_text("from infra.preview_cache import PreviewCache\n")
    monkeypatch.setattr(sys.modules[__name__], "_PROJECT_ROOT", tmp_path)
    assert ("api/probe.py", "infra.preview_cache") in _layer_violations("api")


class TestDocumentAgentServicesAreFrameworkFree:
    """The document-agent services reach infrastructure through ports only.

    Rasterising a page was inlined in `NavigationService` — PIL, a filesystem
    read and an import of another service, in the middle of a use case. The
    `PageRasterizer` port moved all three behind `infra/page_raster.py`; this
    is what stops them coming back. PIL is checked on these modules only; the
    PDF libraries are forbidden in all of `services/` further down.
    """

    MODULES = (
        "navigation_service",
        "citation_service",
        "citation_image_service",
        "parse_loader",
        "source_service",
    )

    # Per-module, not one shared set. `show_sources` (#363) legitimately
    # composes the reading and citing services (the composition root injects
    # them, exactly as `NavigationService` already takes a `CitationService`),
    # and widening a single allow-list to let it would have stopped the rule
    # biting for the four modules that came first.
    PEERS: ClassVar[dict[str, set[str]]] = {
        "navigation_service": {
            "citation_service",
            "navigation_config",
            "navigation_errors",
            "parse_loader",
        },
        "citation_service": {"navigation_config", "navigation_errors", "parse_loader"},
        "citation_image_service": {"navigation_config", "navigation_errors", "parse_loader"},
        "parse_loader": {"navigation_config", "navigation_errors"},
        "source_service": {
            "citation_service",
            "navigation_config",
            "navigation_errors",
            "navigation_service",
            "parse_loader",
        },
    }

    @pytest.mark.parametrize("lib", ["PIL", "pdf2image", "fastapi"])
    def test_no_imaging_or_web_framework(self, lib: str):
        for module in self.MODULES:
            source = (Path(_PROJECT_ROOT) / "services" / f"{module}.py").read_text()
            tree = ast.parse(source)
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            assert lib not in imported, f"services/{module}.py imports '{lib}'"

    @pytest.mark.parametrize("module", MODULES)
    def test_they_do_not_import_an_unexpected_peer_service(self, module: str):
        """A service reaching into another service is a missing port —
        unless the composition root injects it, which the allow-list records."""
        allowed = self.PEERS[module]
        source = (Path(_PROJECT_ROOT) / "services" / f"{module}.py").read_text()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("services."):
                peer = node.module.split(".")[1]
                assert peer in allowed, (
                    f"services/{module}.py imports peer service '{peer}' — add a port, or "
                    "record the injection in PEERS with a reason"
                )


# ---------------------------------------------------------------------------
# External dependency rules (ast-based)
# ---------------------------------------------------------------------------

_DOMAIN_FORBIDDEN_EXTERNALS = {"fastapi", "sqlalchemy", "httpx", "opensearchpy"}
# Packages whose application imports belong exclusively in `infra/`. Adding
# one here prevents services from bypassing the corresponding domain port.
_SERVICES_FORBIDDEN_EXTERNALS = {
    "cryptography",
    "docling",
    "docling_core",
    "fastapi",
    "httpx",
    "neo4j",
    "opensearchpy",
    "pdf2image",
    "pypdfium2",
    "starlette",
}

# Service imports that should move behind ports before joining the denylist.
# Keep this list explicit: deleting a candidate means its migration must also
# add the package to `_SERVICES_FORBIDDEN_EXTERNALS`.
_SERVICES_EXTERNAL_MIGRATION_CANDIDATES: set[str] = set()


class TestDomainExternalDependencies:
    """domain must not import infrastructure-specific third-party libraries."""

    @pytest.mark.parametrize("lib", sorted(_DOMAIN_FORBIDDEN_EXTERNALS))
    def test_domain_does_not_import_external(self, lib: str):
        imports = _collect_imports("domain")
        assert lib not in imports, f"domain imports forbidden external library '{lib}'"


class TestServicesExternalDependencies:
    """services must not import API or adapter implementation packages."""

    @pytest.mark.parametrize("lib", sorted(_SERVICES_FORBIDDEN_EXTERNALS))
    def test_services_does_not_import_external(self, lib: str):
        imports = _collect_imports("services")
        assert lib not in imports, f"services imports forbidden external library '{lib}'"

    def test_service_adapter_candidates_remain_explicit(self):
        """Migration candidates cannot silently disappear from the inventory."""
        imports = _collect_imports("services")
        assert imports >= _SERVICES_EXTERNAL_MIGRATION_CANDIDATES, (
            "A service adapter candidate was removed; add it to "
            "_SERVICES_FORBIDDEN_EXTERNALS or update the inventory."
        )


# ---------------------------------------------------------------------------
# Services never touch the filesystem (ast-based)
# ---------------------------------------------------------------------------

# Stored files are reached through ports (`DocumentFileStore`, `PdfInspector`,
# `PageRasterizer`, ...): a service handles the path strings, never the disk.
_SERVICES_FORBIDDEN_FILESYSTEM_MODULES = {"glob", "os", "shutil", "tempfile"}
# `PurePath` only splits strings; `Path` and the module itself reach the disk.
_PURE_PATHLIB_NAMES = {"PurePath", "PurePosixPath", "PureWindowsPath"}


def _filesystem_access(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _SERVICES_FORBIDDEN_FILESYSTEM_MODULES or root == "pathlib":
                    found.add(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in _SERVICES_FORBIDDEN_FILESYSTEM_MODULES:
                found.add(f"from {node.module} import")
            elif root == "pathlib":
                found.update(
                    f"from pathlib import {alias.name}"
                    for alias in node.names
                    if alias.name not in _PURE_PATHLIB_NAMES
                )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "open"
        ):
            found.add("open()")
    return found


def _services_filesystem_access() -> set[tuple[str, str]]:
    accesses: set[tuple[str, str]] = set()
    for py_file in (_PROJECT_ROOT / "services").rglob("*.py"):
        if any(part in _SKIP_PATH_PARTS for part in py_file.parts):
            continue
        source = str(py_file.relative_to(_PROJECT_ROOT))
        tree = ast.parse(py_file.read_text(), filename=source)
        accesses.update((source, access) for access in _filesystem_access(tree))
    return accesses


def test_services_do_not_touch_the_filesystem():
    accesses = _services_filesystem_access()
    assert not accesses, f"Filesystem access in services, add a port: {sorted(accesses)}"


def test_filesystem_scanner_detects_each_access(tmp_path, monkeypatch):
    """Guard against a green suite when the scanner sees nothing."""
    source = tmp_path / "services" / "probe.py"
    source.parent.mkdir()
    source.write_text(
        "import os.path\n"
        "from shutil import rmtree\n"
        "from pathlib import Path, PurePath\n"
        "open('x')\n"
        "PurePath('a.pdf').stem\n"
    )
    monkeypatch.setattr(sys.modules[__name__], "_PROJECT_ROOT", tmp_path)
    assert _services_filesystem_access() == {
        ("services/probe.py", "import os.path"),
        ("services/probe.py", "from shutil import"),
        ("services/probe.py", "from pathlib import Path"),
        ("services/probe.py", "open()"),
    }


# ---------------------------------------------------------------------------
# Convention: ports live exclusively in domain.ports
# ---------------------------------------------------------------------------


class TestPortConvention:
    """Protocol definitions (ports) must live in domain.ports only."""

    def test_no_protocol_outside_domain_ports(self):
        """No Protocol subclass should be defined outside domain/ports.py."""
        ports_file = Path(_PROJECT_ROOT) / "domain" / "ports.py"
        for py_file in Path(_PROJECT_ROOT).rglob("*.py"):
            if py_file == ports_file:
                continue
            if "tests" in py_file.parts or any(part in _SKIP_PATH_PARTS for part in py_file.parts):
                continue
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        base_name = _get_name(base)
                        if base_name == "Protocol":
                            pytest.fail(
                                f"Protocol '{node.name}' defined in {py_file.relative_to(_PROJECT_ROOT)}"
                                f" — ports must live in domain/ports.py"
                            )


def _get_name(node: ast.expr) -> str:
    """Extract a simple name from an AST expression node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""
