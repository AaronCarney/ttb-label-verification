"""Application stub — minimum surface E4 needs.

The full Application contract is E5/E6 territory; this stub only closes the
E1 omission so the Orchestrator seam (E4 T2 Cycle B) can import it.
"""
from app.schemas.application import Application


def test_application_constructs_with_required_fields():
    a = Application(application_id="A-001", evaluation_id="EV-001")
    assert a.application_id == "A-001"
    assert a.evaluation_id == "EV-001"


def test_application_is_frozen_extra_forbid():
    a = Application(application_id="A-001", evaluation_id="EV-001")
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Application(application_id="A-001", evaluation_id="EV-001", unknown_field="x")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        a.application_id = "A-002"  # type: ignore[misc]
