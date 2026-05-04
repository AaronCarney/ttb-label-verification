"""FR-303 invariant readiness: Refined has no disposition-style field.

This is the schema-side gate. The full structural invariant (covers task
output schemas too) lands in T7."""
from app.schemas.refined import Refined


def test_refined_has_no_disposition_field():
    field_names = set(Refined.model_fields.keys())
    forbidden = {n for n in field_names if "disposition" in n.lower()}
    assert forbidden == set(), f"disposition-style fields leaked: {forbidden}"


def test_refined_has_no_pass_or_fail_field():
    field_names = set(Refined.model_fields.keys())
    assert "pass" not in field_names
    assert "fail" not in field_names


def test_refined_carries_evaluation_id():
    """Sanity: per ARCH §6.6, Refined still keys to an evaluation_id."""
    assert "evaluation_id" in Refined.model_fields
