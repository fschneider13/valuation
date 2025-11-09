from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, confloat

from .common import MonthlySchedule, SeasonalPattern, RampUpSettings


class RevenueRecognitionModel(str, Enum := __import__("enum").Enum):  # quick enum helper
    SUBSCRIPTION = "subscription"
    SERVICES = "services"
    TRANSACTIONAL = "transactional"


class RevenuePlan(BaseModel):
    name: str
    recognition: RevenueRecognitionModel = RevenueRecognitionModel.SUBSCRIPTION
    initial_customers: float
    initial_arpa: float = Field(..., description="Average revenue per account/month")
    new_customers: MonthlySchedule
    churn_rate: MonthlySchedule = Field(..., description="Logo churn per month")
    expansion_rate: MonthlySchedule = Field(default_factory=lambda: MonthlySchedule(default=0.0))
    contraction_rate: MonthlySchedule = Field(default_factory=lambda: MonthlySchedule(default=0.0))
    discount_rate: MonthlySchedule = Field(default_factory=lambda: MonthlySchedule(default=0.0))
    arpa_growth_rate: MonthlySchedule = Field(default_factory=lambda: MonthlySchedule(default=0.0))
    seasonal_pattern: SeasonalPattern = Field(default_factory=SeasonalPattern.flat)
    ramp_up: RampUpSettings = Field(default_factory=RampUpSettings)
    revenue_deferral_months: int = 0
    services_attach_rate: float = 0.0
    services_asp: float = 0.0
    transactional_rate: float = 0.0
    transactional_volume: MonthlySchedule = Field(default_factory=lambda: MonthlySchedule(default=0.0))
    transactional_fee: float = 0.0


class RevenueModel(BaseModel):
    plans: List[RevenuePlan]
    other_recurring_revenue: MonthlySchedule = Field(default_factory=lambda: MonthlySchedule(default=0.0))
    professional_services_revenue: MonthlySchedule = Field(default_factory=lambda: MonthlySchedule(default=0.0))
    adjustments: Dict[str, float] = Field(default_factory=dict)


class RevenueProjection(BaseModel):
    plan_name: str
    customers: float
    revenue: float
    churned_revenue: float
    expansion_revenue: float
    new_customers: float


class RevenueSummary(BaseModel):
    total_gross: float
    total_net: float
    total_churn: float
    total_expansion: float
    arr: float

