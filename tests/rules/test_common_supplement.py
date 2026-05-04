"""Common-pack supplement: FR-204 (type_size_check stretch stub) + heading_phrase
(closes equality_match orphan). Pos+neg ACs for each rule, end-to-end via
VALIDATOR_REGISTRY through a loaded RuleSet.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import app.rules._validators.abv_band  # noqa: F401
import app.rules._validators.contrast_ratio_check  # noqa: F401
import app.rules._validators.cpi_lookup  # noqa: F401
import app.rules._validators.equality_match  # noqa: F401
import app.rules._validators.format_check  # noqa: F401
import app.rules._validators.fuzzy_brand  # noqa: F401
import app.rules._validators.heading_style_check  # noqa: F401
import app.rules._validators.layout_check  # noqa: F401
import app.rules._validators.presence_check  # noqa: F401
import app.rules._validators.type_size_check  # noqa: F401
import app.rules._validators.verbatim_hash  # noqa: F401
from app.rules._validators import VALIDATOR_REGISTRY
from app.rules.loader import YamlRuleLoader
from app.schemas.expected import BeverageClass
from app.schemas.rejection import Outcome
from tests.rules.fixtures import make_context, make_expected, make_obs


@pytest.fixture(scope="module")
def ruleset():
    return YamlRuleLoader().load(Path("rules"))


def _r(rs, rid):
    return next(r for r in rs.rules if r.rule_id == rid)


def _ctx(rs):
    return make_context(assets=rs.assets, decision_tables=rs.decision_tables)


def test_fr204_type_size_min_pos(ruleset) -> None:
    rule = _r(ruleset, "common.warning.type_size_min")
    obs = make_obs(
        field_id="warning_block",
        value={"type_size_pt": 2.5},
        beverage_class=BeverageClass.SPIRITS,
    )
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.PASS


def test_fr204_type_size_min_neg(ruleset) -> None:
    rule = _r(ruleset, "common.warning.type_size_min")
    obs = make_obs(
        field_id="warning_block",
        value={"type_size_pt": 1.5},
        beverage_class=BeverageClass.SPIRITS,
    )
    res = VALIDATOR_REGISTRY[rule.validator](obs, make_expected(field_id="warning_block"), rule, _ctx(ruleset))
    assert res.outcome is Outcome.FAIL
    assert res.reason_code == "WARNING.TYPE_SIZE.UNDER_MIN"


def test_heading_phrase_pos(ruleset) -> None:
    rule = _r(ruleset, "common.warning.heading_phrase")
    obs = make_obs(field_id="warning_heading", value="GOVERNMENT WARNING:", beverage_class=BeverageClass.SPIRITS)
    exp = make_expected(field_id="warning_heading", value="Government Warning:")
    res = VALIDATOR_REGISTRY[rule.validator](obs, exp, rule, _ctx(ruleset))
    assert res.outcome is Outcome.PASS


def test_heading_phrase_neg(ruleset) -> None:
    rule = _r(ruleset, "common.warning.heading_phrase")
    obs = make_obs(field_id="warning_heading", value="WARNING NOTICE:", beverage_class=BeverageClass.SPIRITS)
    exp = make_expected(field_id="warning_heading", value="GOVERNMENT WARNING:")
    res = VALIDATOR_REGISTRY[rule.validator](obs, exp, rule, _ctx(ruleset))
    assert res.outcome is Outcome.FAIL
    assert res.reason_code == "WARNING.VERBATIM.MISMATCH"
