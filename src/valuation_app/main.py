from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, HTTPException

from .schemas import (
    ScenarioCompareResponse,
    ScenarioCreateRequest,
    ScenarioCreateResponse,
    ScenarioListResponse,
    ScenarioRunRequest,
    ScenarioRunResponse,
)
from .models.scenario import ScenarioInput
from .services.calculator import ScenarioCalculator


app = FastAPI(title="Startup Valuation Engine", version="0.1.0")

SCENARIOS: Dict[str, ScenarioInput] = {}
calculator = ScenarioCalculator()


@app.post("/scenarios", response_model=ScenarioCreateResponse)
def create_scenario(payload: ScenarioCreateRequest) -> ScenarioCreateResponse:
    scenario = payload.scenario
    SCENARIOS[scenario.meta.id] = scenario
    return ScenarioCreateResponse(scenario_id=scenario.meta.id)


@app.get("/scenarios", response_model=ScenarioListResponse)
def list_scenarios() -> ScenarioListResponse:
    return ScenarioListResponse(scenarios=list(SCENARIOS.keys()))


@app.post("/run", response_model=ScenarioRunResponse)
def run_scenario(payload: ScenarioRunRequest) -> ScenarioRunResponse:
    scenario: ScenarioInput | None = None
    if payload.scenario is not None:
        scenario = payload.scenario
    elif payload.scenario_id:
        scenario = SCENARIOS.get(payload.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if payload.months:
        scenario = scenario.copy(update={"timeframe": scenario.timeframe.copy(update={"months": payload.months})})
    result = calculator.run(scenario)
    return ScenarioRunResponse(result=result)


@app.get("/scenarios/{scenario_id}", response_model=ScenarioRunResponse)
def get_scenario_projection(scenario_id: str) -> ScenarioRunResponse:
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    result = calculator.run(scenario)
    return ScenarioRunResponse(result=result)


@app.get("/scenarios/{scenario_id}/compare", response_model=ScenarioCompareResponse)
def compare_scenarios(scenario_id: str, ids: str) -> ScenarioCompareResponse:
    base_ids = [scenario_id] + [part for part in ids.split(",") if part]
    valuations = []
    for _id in base_ids:
        scenario = SCENARIOS.get(_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail=f"Scenario {_id} not found")
        result = calculator.run(scenario)
        valuations.append(result.valuation.dcf.enterprise_value)
    return ScenarioCompareResponse(scenario_ids=base_ids, valuation=valuations)


@app.get("/health")
def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}

