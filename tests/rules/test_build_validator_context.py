"""RuleEngine.build_validator_context — abstract-method seam.

Validates the abstract method on the concrete YamlRuleEngine wired via T0a's
build_rule_engine factory: sources assets/decision_tables/engine_version off
the engine's private ruleset; supplies the per-evaluation clock from the
caller. The FakeRuleEngine implementation is exercised in T3's test
(test_fakes_orchestrator_rules.py) so this file stays focused on production.
"""
from app.config import Settings
from app.rules import build_rule_engine
from app.rules._validators import ValidatorContext
from app.rules.context import build_validator_context  # thin shim → engine method


def test_yaml_engine_build_validator_context_returns_validator_context():
    engine = build_rule_engine(Settings())
    ctx = engine.build_validator_context(started_at_ms=12345)
    assert isinstance(ctx, ValidatorContext)


def test_yaml_engine_build_validator_context_sources_from_ruleset():
    engine = build_rule_engine(Settings())
    ctx = engine.build_validator_context(started_at_ms=99)
    assert ctx.assets == engine._ruleset.assets
    assert ctx.decision_tables == engine._ruleset.decision_tables
    assert ctx.started_at_ms == 99
    assert ctx.engine_version  # non-empty (sourced from RuleSet.version)


def test_shim_delegates_to_engine_method():
    """The free-function shim is a one-line forwarder so existing recipes that
    prefer the free-function name still work — but the contract lives on the
    abstraction."""
    engine = build_rule_engine(Settings())
    via_method = engine.build_validator_context(started_at_ms=7)
    via_shim = build_validator_context(engine, started_at_ms=7)
    assert via_method == via_shim
