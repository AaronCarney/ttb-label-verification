"""Cross-cutting registry invariants:

  1. Importing app.rules._validators populates VALIDATOR_REGISTRY with at least
     the names this epoch ships (15 functions across 10 files; 15 registered
     names — L1 §2.1's '12 registered names' is the original target; the surface
     grew to 15 during L2 decomposition because abv_band split into 3 names per
     D-006 and layout_check split into 2 per FR-206/FR-226).
  2. Every *.py file under app/rules/_validators/ (excluding __init__) registers
     at least one name (orphan-validator detection — file→registry direction).
     The companion check (registry→YAML: every registered name is referenced
     by ≥1 rule) lives in T28 because it requires the loaded RuleSet.
  3. No file under app/rules/_validators/ contains the literal 'CFR' outside
     a docstring (L1 §4 exit-gate item 10).
  4. No file under app/rules/ imports openai, anthropic, or httpx
     (L1 §4 exit-gate item 11).
"""
from __future__ import annotations

import ast
import importlib
import pkgutil
import re
from pathlib import Path

EXPECTED_NAMES = {
    "equality_match", "enumerated_match",
    "presence_check", "conditional_presence",
    "regex_match",
    "verbatim_hash",
    "abv_band", "abv_class_boundary_check", "abv_hard_floor",
    "cpi_lookup",
    "heading_style_check",
    "contrast_ratio_check",
    "layout_isolation_check", "same_field_of_vision_check",
    "fuzzy_brand",
}


def _import_all_validators() -> None:
    pkg = importlib.import_module("app.rules._validators")
    for mod in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"app.rules._validators.{mod.name}")


def test_registry_has_expected_names() -> None:
    _import_all_validators()
    from app.rules._validators import VALIDATOR_REGISTRY
    missing = EXPECTED_NAMES - set(VALIDATOR_REGISTRY)
    assert not missing, f"missing registrations: {missing}"


def test_every_validator_module_registers_at_least_one_name() -> None:
    _import_all_validators()
    pkg_root = Path("app/rules/_validators")
    py_files = [p for p in pkg_root.glob("*.py") if p.name != "__init__.py"]
    from app.rules._validators import VALIDATOR_REGISTRY
    by_module: dict[str, int] = {}
    for fn in VALIDATOR_REGISTRY.values():
        by_module[fn.__module__] = by_module.get(fn.__module__, 0) + 1
    for p in py_files:
        mod_name = f"app.rules._validators.{p.stem}"
        assert by_module.get(mod_name, 0) >= 1, f"orphan validator file: {p}"


def test_no_cfr_string_literal_in_validator_code() -> None:
    """Citation strings live in YAML, never in Python (L1 §4 #10)."""
    pkg_root = Path("app/rules/_validators")
    bad: list[str] = []
    for path in pkg_root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "CFR" in node.value:
                    if isinstance(getattr(node, "parent", None), ast.Expr):
                        continue  # docstring/expression statement (best-effort)
                    bad.append(f"{path.name}:{node.lineno}: {node.value!r}")
    assert not bad, "validator files contain 'CFR' literals: " + "; ".join(bad)


def test_no_inference_dependency_imports_under_app_rules() -> None:
    """L1 §4 #11: rule engine has no inference dependency."""
    banned = re.compile(r"^\s*(?:from|import)\s+(openai|anthropic|httpx)\b", re.MULTILINE)
    rules_root = Path("app/rules")
    bad: list[str] = []
    for path in rules_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for match in banned.finditer(text):
            bad.append(f"{path}:{text[:match.start()].count(chr(10))+1}: {match.group(0).strip()}")
    assert not bad, "banned imports under app/rules/: " + "; ".join(bad)
