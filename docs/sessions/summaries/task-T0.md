## Task T0 — OverrideEntry.field_name Optional

Relaxed `OverrideEntry.field_name` from `str` to `str | None = None` in `app/schemas/audit.py`, enabling whole-envelope overrides where no specific field is targeted (L1 §2.6).

**Files modified:**
- `app/schemas/audit.py` — single-line change on `field_name`
- `tests/test_override_entry_field_name_optional.py` — new file (4 tests)

**Test count:** 4 added, all green.

**Deviations:** None. Full suite errors (rapidfuzz, respx missing from system Python) are pre-existing environment gaps outside this task's scope.
