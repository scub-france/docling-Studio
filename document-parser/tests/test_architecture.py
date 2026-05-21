"""Hexagonal architecture tests — enforce layer dependency rules.

Uses pytestarch for inter-layer dependency rules and ast-based import
scanning for external (third-party) dependency constraints.

Rules enforced:
- domain   -> no import from api, services, infra, persistence
- services -> no import from api, infra, persistence
- api      -> no import from infra, persistence
- infra    -> no import from api, services
- persistence -> no import from api, services, infra
- domain   -> no import of fastapi, sqlalchemy, httpx, opensearchpy
- services -> no import of fastapi
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestarch = pytest.importorskip(
    "pytestarch",
    reason="pytestarch not installed — `pip install -r requirements-test.txt` to enforce layer rules",
)
Rule = pytestarch.Rule
get_evaluable_architecture = pytestarch.get_evaluable_architecture

# ---------------------------------------------------------------------------
# pytestarch evaluable (project root = document-parser/)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_SKIP_PATH_PARTS = {"__pycache__", ".venv", ".ruff_cache", "uploads", "data"}

_PYTESTARCH_EXCLUSIONS = (
    "*__pycache__*",
    "*.pyc",
    "*.lock",
    "*.sqlite*",
    "*.db",
    "*.json",
    "*.log",
    "*.pdf",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.svg",
    "*.ico",
    "*.bin",
    "*.so",
    "*.dylib",
    "*.dll",
    "*.a",
    "*.o",
    "*.whl",
    "*.egg-info*",
    "*.dist-info*",
    "*.venv*",
    "*.ruff_cache*",
    "*uploads*",
    "*data*",
)

# pytestarch uses the directory name as module prefix when given absolute paths.
# We use the directory name to build qualified module references.
_PREFIX = _PROJECT_ROOT.name  # "document-parser"

_evaluable = get_evaluable_architecture(
    str(_PROJECT_ROOT),
    str(_PROJECT_ROOT),
    exclusions=_PYTESTARCH_EXCLUSIONS,
)


def _mod(layer: str) -> str:
    """Return the fully-qualified pytestarch module name for a layer."""
    return f"{_PREFIX}.{layer}"


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
# Inter-layer dependency rules (pytestarch)
# ---------------------------------------------------------------------------


class TestDomainLayerIsolation:
    """domain must not depend on any other layer."""

    @pytest.mark.parametrize("forbidden", ["api", "services", "infra", "persistence"])
    def test_domain_does_not_import(self, forbidden: str):
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(_mod("domain"))
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(_mod(forbidden))
        )
        rule.assert_applies(_evaluable)


class TestServicesLayerIsolation:
    """services may import domain only."""

    @pytest.mark.parametrize("forbidden", ["api", "infra", "persistence"])
    def test_services_does_not_import(self, forbidden: str):
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(_mod("services"))
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(_mod(forbidden))
        )
        rule.assert_applies(_evaluable)


class TestApiLayerIsolation:
    """api may import services and domain, but not infra or persistence."""

    @pytest.mark.parametrize("forbidden", ["infra", "persistence"])
    def test_api_does_not_import(self, forbidden: str):
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(_mod("api"))
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(_mod(forbidden))
        )
        rule.assert_applies(_evaluable)


class TestInfraLayerIsolation:
    """infra may import domain (ports), but not api or services."""

    @pytest.mark.parametrize("forbidden", ["api", "services"])
    def test_infra_does_not_import(self, forbidden: str):
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(_mod("infra"))
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(_mod(forbidden))
        )
        rule.assert_applies(_evaluable)


class TestPersistenceLayerIsolation:
    """persistence may import domain, but not api, services, or infra."""

    @pytest.mark.parametrize("forbidden", ["api", "services", "infra"])
    def test_persistence_does_not_import(self, forbidden: str):
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(_mod("persistence"))
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(_mod(forbidden))
        )
        rule.assert_applies(_evaluable)


# ---------------------------------------------------------------------------
# External dependency rules (ast-based)
# ---------------------------------------------------------------------------

_DOMAIN_FORBIDDEN_EXTERNALS = {"fastapi", "sqlalchemy", "httpx", "opensearchpy"}
_SERVICES_FORBIDDEN_EXTERNALS = {"fastapi"}


class TestDomainExternalDependencies:
    """domain must not import infrastructure-specific third-party libraries."""

    @pytest.mark.parametrize("lib", sorted(_DOMAIN_FORBIDDEN_EXTERNALS))
    def test_domain_does_not_import_external(self, lib: str):
        imports = _collect_imports("domain")
        assert lib not in imports, f"domain imports forbidden external library '{lib}'"


class TestServicesExternalDependencies:
    """services must not import web-framework libraries."""

    @pytest.mark.parametrize("lib", sorted(_SERVICES_FORBIDDEN_EXTERNALS))
    def test_services_does_not_import_external(self, lib: str):
        imports = _collect_imports("services")
        assert lib not in imports, f"services imports forbidden external library '{lib}'"


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
