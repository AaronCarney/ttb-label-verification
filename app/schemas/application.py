"""Application input identity (E1-omission closer for E4 orchestrator seam).

The full Application contract — applicant, formula, type_of_application, labels,
etc. — lives in `app/schemas/wire/application.py::ApplicationEnvelope`. This
module exposes only the identity surface (`application_id`, `evaluation_id`) the
Orchestrator + downstream services key off. E5 may extend this with additional
fields; until then, keep the stub minimal so no orchestrator test depends on
fields that aren't pinned by L1.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.expected import ExpectedValue


class Application(BaseModel):
    """Identity surface for an in-flight evaluation. Extend in E5 if needed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    application_id: str
    evaluation_id: str
    expected_values: tuple[ExpectedValue, ...] = ()
