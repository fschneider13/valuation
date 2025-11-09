from __future__ import annotations

from typing import List, Optional

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .models.results import ScenarioResult
from .models.scenario import ScenarioInput


class ScenarioCreateRequest(BaseModel):
    scenario: ScenarioInput
    clone_from: Optional[str] = Field(default=None, description="Scenario ID to clone from")


class ScenarioCreateResponse(BaseModel):
    scenario_id: str


class ScenarioRunRequest(BaseModel):
    scenario_id: Optional[str] = None
    scenario: Optional[ScenarioInput] = None
    months: Optional[int] = None


class ScenarioListResponse(BaseModel):
    scenarios: List[str]


class ScenarioCompareResponse(BaseModel):
    scenario_ids: List[str]
    valuation: List[float]


class ScenarioRunResponse(BaseModel):
    result: ScenarioResult

