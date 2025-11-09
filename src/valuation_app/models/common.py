from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, conint, confloat


class ScenarioType(str, Enum):
    BASE = "base"
    BULL = "bull"
    BEAR = "bear"


class CurrencySettings(BaseModel):
    base_currency: str = Field(..., description="ISO currency code used for calculations")
    display_currency: str = Field(..., description="ISO currency code used for presentation")
    fx_rate: float = Field(1.0, description="FX rate display/base. Allows conversion when currencies differ.")


class InflationIndex(BaseModel):
    name: str
    annual_rate: float = Field(..., description="Annual inflation rate as decimal (e.g. 0.04 for 4%)")

    def monthly_factor(self) -> float:
        return (1 + self.annual_rate) ** (1 / 12) - 1


class TimeframeSettings(BaseModel):
    start_date: date
    months: conint(ge=1)


class ScenarioMeta(BaseModel):
    id: str
    name: str
    scenario_type: ScenarioType = ScenarioType.BASE
    timezone: str = "America/Sao_Paulo"
    description: Optional[str] = None


class PriceAdjustment(BaseModel):
    indexer: Optional[InflationIndex] = None
    custom_monthly_rate: float = 0.0

    def factor_for_month(self, month_index: int) -> float:
        base = self.custom_monthly_rate
        if self.indexer is not None:
            base += self.indexer.monthly_factor()
        return base


class MonthlySchedule(BaseModel):
    default: float
    adjustments: Dict[int, float] = Field(default_factory=dict, description="Overrides keyed by 0-based month index")

    def value_for(self, month_index: int) -> float:
        return self.adjustments.get(month_index, self.default)


class SeasonalPattern(BaseModel):
    values: List[float] = Field(..., description="Length-12 seasonal multipliers")

    @classmethod
    def flat(cls) -> "SeasonalPattern":
        return cls(values=[1.0] * 12)

    def factor(self, month_index: int) -> float:
        return self.values[month_index % 12]


class RampUpSettings(BaseModel):
    months: conint(ge=1) = 1
    factor: confloat(ge=0, le=1) = 1.0

    def completion(self, month_index: int) -> float:
        return min(1.0, (month_index + 1) / self.months) * self.factor


class AuditInfo(BaseModel):
    created_by: str
    created_at: date
    updated_by: Optional[str] = None
    updated_at: Optional[date] = None


class CompanyState(BaseModel):
    as_of: date
    cash: float
    accounts_receivable: float = 0.0
    accounts_payable: float = 0.0
    inventory: float = 0.0
    fixed_assets: float = 0.0
    accumulated_depreciation: float = 0.0
    debt: float = 0.0
    equity: float = 0.0

    def net_fixed_assets(self) -> float:
        return max(0.0, self.fixed_assets - self.accumulated_depreciation)

