# Epoch 2 — Rule Engine + YAML Rule Pack

> **Parent:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md)
> **Tier:** L1 (epoch-level).
> **Substitutability seam owned:** `RuleLoader` (data-shape, MVP-substitutable per ARCH §8.3); `RuleEngine` ABC declared but only `YamlRuleEngine` shipped (per ARCH §8.4 — engine code not substitutable in MVP, but data-shape is).
> **Depends on:** **E1** (`app/schemas/rules.py`, `app/schemas/extracted.py`, `app/schemas/expected.py`, `app/schemas/rejection.py`).

---

## 1. Goal

Ship the deterministic core. Given a `FieldObservation` and an `ExpectedValue`, the rule engine returns a `ValidationResult` with disposition (`pass | fail | needs_review | not_applicable`), reason code, CFR citation, evidence, and confidence — fully exercised against unit fixtures with **no vision and no orchestrator** in the picture.

This epoch is the regulatory-literacy proof. After E2 closes, every PRD FR-200/210/220/230 series rule has at least one positive AC and one canonical negative AC asserting the right `reason_code` + CFR citation, the brand-match policy from ARCH §6.11 is exercised, and the RuleLoader fail-closes on every cross-check in S5 §d.

---

## 2. Components delivered

### 2.1 Rule loader and engine (`app/rules/`)

- `app/rules/engine.py` — `RuleEngine` ABC with one async method `evaluate(observations: list[FieldObservation], expected: list[ExpectedValue], context: ValidatorContext) -> list[ValidationResult]`.
- `app/rules/yaml_engine.py` — `YamlRuleEngine` concrete implementation; the only one in MVP.
- `app/rules/loader.py` — `YamlRuleLoader.load(rules_dir: Path) -> RuleSet` walks `rules/` recursively, validates each rule via Pydantic v2, runs the S5 §d cross-checks (rule_id uniqueness, reason-code registry completeness, asset hash pin, decision-table ref present, `test_fixtures` non-empty, validator-name whitelist, version range, asset hash drift). **Fail-closed** — any violation raises `RuleLoaderError` and the FastAPI startup hook re-raises so `uv run task demo` exits non-zero with the violation list.
- `app/rules/models.py` — `RuleSet`, `RuleDefinition`, `MatchPolicy` enum, `ReasonCodeEntry`, `AssetRef`, `DecisionTable`. **Note:** declared in E1 (`app/schemas/rules.py`); E2 re-exports / consumes them. The L2 plan settles whether the canonical home is `app/schemas/rules.py` (E1) or `app/rules/models.py` (E2) — recommend the former with a re-export from the latter for namespace ergonomics.
- `app/rules/brand_match.py` — Stage A normalized exact + Stage B Jaro-Winkler per ARCH §6.11. Uses `rapidfuzz`. Threshold values come from rule-pack data (`pass_threshold: 0.92`, `needs_review_threshold: 0.85`), not from constants.

### 2.2 Validator registry (`app/rules/_validators/`)

- `app/rules/_validators/__init__.py` — `VALIDATOR_REGISTRY: dict[str, Callable]`; `register(name)` decorator; whitelist iteration for the loader's S5 §d cross-check.
- `app/rules/_validators/equality_match.py` — exact / case-insensitive / normalized equality; serves brand-name and class/type presence rules.
- `app/rules/_validators/verbatim_hash.py` — sha256 hash compare against `assets/warnings/govt_warning_16_21.txt` for FR-201; emits `WARNING.VERBATIM.MISMATCH` on drift.
- `app/rules/_validators/abv_band.py` — class-aware ABV tolerance per D-006 (spirits ±0.3 pp, malt ±0.3 pp + 0.5% hard floor, wine ±1.0 pp >14% / ±1.5 pp ≤14% with class-boundary anti-overlap §4.36(c)). Uses `Decimal` arithmetic per S5 §c.
- `app/rules/_validators/cpi_lookup.py` — cardinal decision-table lookup against `rules/tables/cpi_16_22_a_4.yaml` with `interpolation: none`; serves FR-205.
- `app/rules/_validators/heading_style_check.py` — caps + bold detection for FR-202 (`WARNING.STYLE.HEADING_NOT_BOLD_CAPS`); consumes typographic properties from `FieldObservation` (extracted by E3 vision in production, mocked in E2 tests).
- `app/rules/_validators/contrast_ratio_check.py` — WCAG-style contrast ratio for FR-203 (Stretch).
- `app/rules/_validators/fuzzy_brand.py` — wraps the `app/rules/brand_match.py` two-stage policy; serves FR-240.
- Plus: `presence_check.py` (generic field-present), `format_check.py` (regex format for ABV statement formats).

### 2.3 Rule pack (`rules/`)

- `rules/common/health_warning.yaml` — Part 16 rules (FR-200 through FR-206).
- `rules/wine/wine.yaml` — Part 4 rules (FR-210 through FR-217).
- `rules/spirits/spirits.yaml` — Part 5 rules (FR-220 through FR-228).
- `rules/malt/malt.yaml` — Part 7 rules (FR-230 through FR-237).
- `rules/spirits-deep.yaml` — spirits-deep rule pack per D-012 (FR-222 SoI match, FR-229 age-statement floor).
- `rules/reason_codes.yaml` — registry per S5 §e: top-level `version`, `bins` mapping, `codes` mapping (`BIN.SUB.SPECIFIC[.QUALIFIER]` → `{description, cfr_anchors, severity}`).
- `rules/tables/cpi_16_22_a_4.yaml` — cardinal CPI table, `interpolation: none`.

### 2.4 Hash-pinned regulatory assets (`assets/`)

- `assets/warnings/govt_warning_16_21.txt` — verbatim §16.21 text. Hash pinned in `rules/common/health_warning.yaml` under `asset:` so the loader's S5 §d cross-check 5(c) detects drift.

### 2.5 Test surface (`tests/rules/`, `tests/`)

- `tests/test_rule_loader_failclose.py` — every S5 §d cross-check failure mode is asserted (unknown validator, missing reason-code in registry, asset hash mismatch, missing test_fixtures, version range mismatch, duplicate rule_id, orphan reason-code, decision-table ref dangling).
- `tests/test_rules_yaml_round_trip.py` — every YAML file in `rules/` loads, validates against `RuleSet`, and survives a model_dump → model_validate round-trip.
- `tests/test_brand_match_policies.py` — the cases from D-012 + ARCH §6.11: `STONE'S THROW` vs `Stone's Throw` resolves at Stage A normalized; `KENTUCKY BOURBON` vs `KEntucky bourbon` Stage A pass; `Mama's Bourbon` vs `Mamas Bourbon` Stage A pass (punctuation strip); `Stone's Throw Bourbon` vs `Stone's Throw Distilling Co.` Stage B fuzzy needs_review band; `Acme` vs `Bizmark` Stage B fail.
- `tests/test_validator_registry.py` — every `app/rules/_validators/*.py` file registers under a stable name; whitelist iteration matches; YAML referencing an unregistered validator name fails at load.
- `tests/rules/test_warning_rules.py` — pos+neg per FR-200, FR-201, FR-202, FR-205, FR-206 (FR-203 / FR-204 stretch — at least one positive AC each).
- `tests/rules/test_wine_rules.py` — pos+neg per FR-210 through FR-217 including the §4.36(c) class-boundary anti-overlap edge.
- `tests/rules/test_spirits_rules.py` — pos+neg per FR-220 through FR-228; FR-225 boundary cases (exactly at ±0.3 pp pass, exactly outside fail).
- `tests/rules/test_malt_rules.py` — pos+neg per FR-230 through FR-237 including the §7.65(c) hard 0.5% floor (FR-235).
- `tests/rules/test_spirits_deep.yaml.py` — FR-222 SoI candidate match, FR-229 age-statement floor.
- `tests/rules/test_reason_code_grammar.py` — `BIN.SUB.SPECIFIC[.QUALIFIER]` regex `^[A-Z][A-Z0-9_]*(?:\.[A-Z][A-Z0-9_]*){2,3}$` accepts every code in `reason_codes.yaml` and rejects representative malformed strings.
- `tests/rules/test_per_rule_timeout.py` — a deliberately slow fake validator triggers the 250 ms per-rule timeout and emits `ENGINE.VALIDATOR.TIMEOUT` (FR-908).
- `tests/rules/test_validator_exception.py` — a fake validator raising `ZeroDivisionError` is caught and emits `ENGINE.VALIDATOR.EXCEPTION` (FR-907) with the exception class in the log; other rules continue.

---

## 3. Wire / data contracts owned by this epoch

E2 owns every YAML file under `rules/` and every asset under `assets/`. The shape of `RuleSet`/`RuleDefinition`/`ReasonCodeEntry` is settled in E1 schemas; E2 fills them.

E2 also owns the **reason-code registry** (`rules/reason_codes.yaml`) and the registry-completeness invariant. After E2 closes, no later epoch may emit a `reason_code` not in the registry — the loader rejects it.

---

## 4. Exit gate

The epoch lands when **all of these pass**:

1. `RuleLoader.load(Path("rules/"))` returns a `RuleSet` with `len(rules) >= 33` (count of FR-200 through FR-237 + FR-240 + spirits-deep FR-222 / FR-229).
2. Every PRD FR-200/210/220/230 series rule has at least one positive AC and one canonical negative AC; `pytest tests/rules/ -v` passes 100% with `>= 70` test cases (≥ 2 per rule × 33+ rules).
3. Boundary cases for ABV tolerance (FR-214, FR-225, FR-234) pass: ABV exactly at the tolerance limit returns `pass`; exactly outside returns `fail`; class-boundary anti-overlap rule (FR-215) fires when triggered.
4. Brand-match Stage A resolves `STONE'S THROW` ↔ `Stone's Throw` to `pass` with `match_kind: normalized` (the AC for D-012 / `PRD-deferred §3.3` Stage-2 narration update).
5. Brand-match Stage B emits `needs_review` for `0.85 <= score < 0.92` and `fail` (`BRAND.NAME.MISMATCH`) for `score < 0.85`.
6. RuleLoader fail-closes on every S5 §d cross-check; `tests/test_rule_loader_failclose.py` covers all 8+ violation modes.
7. The `assets/warnings/govt_warning_16_21.txt` file's sha256 matches the hash pinned in `rules/common/health_warning.yaml`; mutating either side fails the loader.
8. Per-rule timeout (250 ms) and validator-exception paths emit FR-908 / FR-907 reason codes correctly; other rules in the same evaluation continue.
9. The reason-code registry has zero orphans (warning emitted at startup if any) and zero unreferenced codes that aren't explicitly marked stretch.
10. `grep -rn 'CFR' app/rules/_validators/ | grep -v 'docstring'` returns no hits — citation strings live in YAML, not in Python (P3 enforcement).
11. `grep -rn 'openai\|anthropic\|httpx' app/rules/` returns no hits — the rule engine has no inference dependencies (P1 enforcement).

---

## 5. TDD strategy

**Test surface (recap from §2.5):** ≥ 11 test files, ≥ 70 assertions across rule-pack ACs, ≥ 8 loader fail-close cases, ≥ 6 brand-match cases.

**Mockable** — clock (for timeout tests via `time.monotonic` injection), filesystem reads (for the asset-hash-drift test).

**Real** — every YAML file in `rules/`; the actual `assets/warnings/govt_warning_16_21.txt`; the actual `rapidfuzz` Jaro-Winkler.

**Fixture style.** Per-rule fixtures live as small Python data builders in `tests/rules/fixtures.py` — `make_obs(field, value, conf=0.95, ...)` — not as YAML files. The rule **set** is YAML; the rule **inputs** in tests are Python builders to keep tests skim-readable.

**Contract test for the validator registry.** Adding a new validator must require: (a) a Python file in `app/rules/_validators/` with `@register("name")` on the callable; (b) at least one rule in `rules/*.yaml` referencing the name; (c) a whitelist entry. Test asserts each `_validators/*.py` file is reachable via the registry and is referenced by ≥ 1 rule (orphan-validator detection).

---

## 6. Out of scope for this epoch

- Class-specific deferrals per D-003 (sulfite, organic, FD&C Yellow #5, cochineal/carmine, allergen, vintage, AVA, appellation) — out of MVP entirely.
- Wine depth, malt depth — **stretch** (see parent §8); when unblocked, they are L2 additions to E2's rule pack, not new L1 epochs.
- Stretch FR-203 contrast / FR-204 type-size beyond a positive-AC stub — full implementations land alongside vision in E3 (since they consume image properties).
- AI orchestration triggers (FR-300/301/302) — the rule engine emits `needs_review` for the borderline brand-match band; **E5** is what calls the orchestrator on that signal.
- Application Service wiring — **E5**.

---

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Rule-pack drift between YAML and the regulation text | Low | High | Hash-pinned `assets/warnings/govt_warning_16_21.txt` is the single source for FR-201; CFR citations are part of every `RuleDefinition.cfr_citation` and surface in the test assertions, so a typo in the YAML is caught by the per-rule AC |
| ABV tolerance off-by-one at the boundary | Medium | Medium | Boundary-case ACs (`exactly at`, `exactly outside`) are explicit in §4 exit gate item 3; `Decimal` arithmetic per S5 §c |
| RuleLoader's startup latency exceeds the 30 s boot budget if the YAML balloons | Low | Medium | Loader is single-pass over `rules/`; asset-hash compute is per-asset (one sha256); benchmarked in the L2 plan as part of the AC |
| Brand-match thresholds hand-tuned without ground truth | Accepted | Low | Default `pass=0.92, needs_review=0.85` per S5 §5 / T3 §Q3.4; automated re-calibration is stretch (PRD §3.2) and lives in E8 |
| Validator registry collisions if two files register the same name | Low | Medium | The `register` decorator raises `ValueError("name already registered")`; asserted by `tests/test_validator_registry.py` |

---

## 8. L2 hand-off notes

When E2 lands, the L2 plan needs to:

1. Decompose validator implementations into **one task per validator file** (10 tasks). Each is small enough for a single TDD cycle: write the failing test (positive + negative case), implement, run.
2. Decompose rule-pack YAML into **one task per pack** (5 tasks: common, wine, spirits, malt, spirits-deep). Each task lands the YAML + registry entries + the `tests/rules/test_<pack>.py` per-rule ACs.
3. **One task** for `RuleLoader` with its 8+ cross-checks; tested via deliberately-malformed YAML files in `tests/rules/malformed/`.
4. **One task** for `YamlRuleEngine` (the `evaluate()` method including per-rule timeout wrapper and exception catch).
5. **One task** for `app/rules/brand_match.py` Stage A + Stage B.
6. **Wave structure:** `models.py` re-exports → validators (parallelizable) → loader (depends on validators registry) → rule-pack YAML (parallelizable, each pack is independent) → engine + brand_match (sequential after loader).

L2 plan **must** include a final task that runs `python -m app.rules.loader rules/` as a CLI smoke against the real `rules/` tree — this proves the loader is wireable before E5 imports it.

---

## 9. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial epoch-2 L1 doc. |
