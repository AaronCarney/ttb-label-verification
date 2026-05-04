"""Pure disposition rule. Source: L1 §10.3 / §2.1 step 7."""
from __future__ import annotations

from typing import Iterable, Literal

from app.schemas.rejection import Outcome, ValidationResult


Disposition = Literal["pass", "fail", "needs_review"]
_PASS_LIKE = {Outcome.PASS, Outcome.NOT_APPLICABLE}


def compute_disposition(results: Iterable[ValidationResult]) -> Disposition:
    """fail iff any FAIL; pass iff every PASS or NOT_APPLICABLE; else needs_review.
    Empty results → needs_review (engine produced nothing — honest failure)."""
    results = tuple(results)
    if not results:
        return "needs_review"
    if any(r.outcome == Outcome.FAIL for r in results):
        return "fail"
    if all(r.outcome in _PASS_LIKE for r in results):
        return "pass"
    return "needs_review"
