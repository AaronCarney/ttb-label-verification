"""FR-200..FR-206 per-rule pos+neg ACs. Each rule is exercised against the
loaded RuleSet by name, so a rename in YAML breaks the test (intentional).
"""
from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

import app.rules._validators.contrast_ratio_check  # noqa: F401
import app.rules._validators.cpi_lookup  # noqa: F401
import app.rules._validators.equality_match  # noqa: F401
import app.rules._validators.format_check  # noqa: F401
import app.rules._validators.fuzzy_brand  # noqa: F401
import app.rules._validators.heading_style_check  # noqa: F401
import app.rules._validators.layout_check  # noqa: F401
import app.rules._validators.presence_check  # noqa: F401
import app.rules._validators.verbatim_hash  # noqa: F401
from app.rules._validators import VALIDATOR_REGISTRY
from app.rules.loader import YamlRuleLoader
from app.schemas.expected import BeverageClass
from app.schemas.rejection import Outcome
from tests.rules.fixtures import make_context, make_expected, make_obs


@pytest.fixture(scope="module")
def ruleset():
    return YamlRuleLoader().load(Path("rules"))


def _by_id(ruleset, rule_id):
    return next(r for r in ruleset.rules if r.rule_id == rule_id)


def _ctx(ruleset):
    return make_context(assets=ruleset.assets, decision_tables=ruleset.decision_tables)


CANONICAL_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. (2) "
    "Consumption of alcoholic beverages impairs your ability to drive a car or operate "
    "machinery, and may cause health problems."
)


def test_fr200_warning_present_pos(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.present")
    obs = make_obs(field_id="warning_block", value=CANONICAL_WARNING, beverage_class=BeverageClass.SPIRITS)
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.PASS


def test_fr200_warning_present_neg(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.present")
    obs = make_obs(field_id="warning_block", value=None, beverage_class=BeverageClass.SPIRITS)
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.FAIL
    assert res.reason_code == "WARNING.PRESENCE.MISSING"


def test_fr201_warning_verbatim_pos(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.verbatim")
    obs = make_obs(field_id="warning_block", value=CANONICAL_WARNING)
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.PASS


def test_fr201_warning_verbatim_neg(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.verbatim")
    obs = make_obs(field_id="warning_block", value=CANONICAL_WARNING.replace("birth defects", "complications"))
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.FAIL
    assert res.reason_code == "WARNING.VERBATIM.MISMATCH"


def test_fr202_heading_style_pos(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.heading_caps_bold")
    obs = make_obs(field_id="warning_block", value={"heading_text": "GOVERNMENT WARNING", "heading_styles": {"weight": "bold", "case": "upper"}})
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.PASS


def test_fr202_heading_style_neg(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.heading_caps_bold")
    obs = make_obs(field_id="warning_block", value={"heading_text": "Government Warning", "heading_styles": {"weight": "bold", "case": "title"}})
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.FAIL
    assert res.reason_code == "WARNING.STYLE.HEADING_NOT_BOLD_CAPS"


def test_fr203_contrast_pos(ruleset) -> None:
    """Stretch — single positive AC per L1 §6."""
    rule = _by_id(ruleset, "common.warning.contrasting_bg")
    obs = make_obs(field_id="warning_block", value={"contrast_ratio": 7.2})
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.PASS


def test_fr205_cpi_pos(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.cpi_max")
    obs = make_obs(field_id="warning_block", value={"cpi": 30, "height_mm": 1})
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.PASS


def test_fr205_cpi_neg(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.cpi_max")
    obs = make_obs(field_id="warning_block", value={"cpi": 50, "height_mm": 1})
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.FAIL
    assert res.reason_code == "WARNING.TYPE_SIZE.CPI_EXCEEDED"


def test_fr206_separate_apart_pos(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.separate_apart")
    obs = make_obs(field_id="warning_block", value={"min_neighbor_distance_px": 10})
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.PASS


def test_fr206_separate_apart_neg(ruleset) -> None:
    rule = _by_id(ruleset, "common.warning.separate_apart")
    obs = make_obs(field_id="warning_block", value={"min_neighbor_distance_px": 1})
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.FAIL
    assert res.reason_code == "WARNING.PLACEMENT.NOT_SEPARATE"
