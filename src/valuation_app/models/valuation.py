from __future__ import annotations

from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field


class TerminalValueMethod(str, Enum):
    PERPETUITY = "perpetuity"
    MULTIPLE = "multiple"


class MultipleMetric(str, Enum):
    REVENUE = "revenue"
    EBITDA = "ebitda"
    ARR = "arr"


class VCExitStrategy(str, Enum):
    IPO = "ipo"
    STRATEGIC = "strategic"
    SECONDARY = "secondary"


class ValuationSettings(BaseModel):
    wacc: float
    perpetual_growth_rate: float
    terminal_method: TerminalValueMethod = TerminalValueMethod.PERPETUITY
    terminal_multiple: float = 0.0
    terminal_multiple_metric: MultipleMetric = MultipleMetric.EBITDA
    exit_year_multiple: float = 0.0
    target_exit_year: int = 5
    discount_rate_vc: float = 0.3
    probability_of_success: float = 1.0
    scorecard_weights: Dict[str, float] = Field(default_factory=dict)


class DiscountedCashFlowResult(BaseModel):
    enterprise_value: float
    equity_value: float
    pv_of_cash_flows: float
    pv_of_terminal_value: float
    terminal_value: float
    discount_factors: List[float]


class MultipleValuationResult(BaseModel):
    metric: MultipleMetric
    multiple: float
    value: float


class VCValuationResult(BaseModel):
    exit_value: float
    ownership_required: float
    post_money: float
    pre_money: float


class ScorecardValuationResult(BaseModel):
    total_score: float
    valuation: float


class ValuationResult(BaseModel):
    dcf: DiscountedCashFlowResult
    multiples: List[MultipleValuationResult]
    vc_method: VCValuationResult
    scorecard: ScorecardValuationResult | None = None

