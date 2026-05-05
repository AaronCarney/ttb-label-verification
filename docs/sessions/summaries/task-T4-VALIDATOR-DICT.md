## T4-VALIDATOR-DICT

**Status:** COMPLETE  
**Commit:** ca2c203

### What changed
- `app/rules/_validators/fuzzy_brand.py`: added `_project_brand` helper; replaced `str(obs.observed_value)` with projected value; added NOT_APPLICABLE branch when `expected` is empty.
- `app/rules/_validators/format_check.py`: added `_project_alc_text` helper; replaced `str(obs.observed_value)` with projected value in `regex_match`.
- `tests/test_validator_dict_observation.py`: 6 new tests covering dict projection + NOT_APPLICABLE.

### Results
- 6/6 focused tests green
- 212/212 rule+validator tests green
