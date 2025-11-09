from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from .common import MonthlySchedule, PriceAdjustment


class SubscriptionCost(BaseModel):
    name: str
    monthly_cost: float
    price_adjustment: PriceAdjustment = Field(default_factory=PriceAdjustment)


class HeadcountPosition(BaseModel):
    role: str
    area: str
    level: str
    current_fte: float
    base_salary: float
    benefits_pct: float = 0.0
    benefits_fixed: float = 0.0
    bonus_pct: float = 0.0
    payroll_taxes_pct: float = 0.0
    subscriptions: List[SubscriptionCost] = Field(default_factory=list)
    salary_adjustment: PriceAdjustment = Field(default_factory=PriceAdjustment)


class HiringPlan(BaseModel):
    role: str
    month_index: int
    quantity: float
    salary_override: float | None = None


class HeadcountModel(BaseModel):
    positions: List[HeadcountPosition]
    hires: List[HiringPlan] = Field(default_factory=list)
    attrition_pct: MonthlySchedule = Field(default_factory=lambda: MonthlySchedule(default=0.0))


class HeadcountCostBreakdown(BaseModel):
    area: str
    salaries: float
    benefits: float
    subscriptions: float
    total: float
    fte: float

