from __future__ import annotations

from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field

from .common import MonthlySchedule, PriceAdjustment


class CostNature(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"


class CostAllocation(str, Enum):
    COGS = "cogs"
    OPEX = "opex"


class CostCenter(str, Enum):
    ENGINEERING = "engineering"
    PRODUCT = "product"
    SALES = "sales"
    MARKETING = "marketing"
    CS = "cs"
    GNA = "gna"
    OTHER = "other"


class CostItem(BaseModel):
    name: str
    nature: CostNature
    allocation: CostAllocation
    cost_center: CostCenter = CostCenter.OTHER
    base_amount: float
    variable_rate: float = 0.0
    driver: str = "revenue"
    price_adjustment: PriceAdjustment = Field(default_factory=PriceAdjustment)
    schedule: MonthlySchedule = Field(default_factory=lambda: MonthlySchedule(default=1.0))


class SupplierContract(BaseModel):
    name: str
    start_month: int
    base_amount: float
    escalation_pct: float = 0.0
    escalation_frequency_months: int = 12
    allocation: CostAllocation = CostAllocation.OPEX
    cost_center: CostCenter = CostCenter.OTHER


class CostModel(BaseModel):
    items: List[CostItem] = Field(default_factory=list)
    supplier_contracts: List[SupplierContract] = Field(default_factory=list)
    cogs_variable_pct: float = 0.0
    cogs_per_customer: float = 0.0


class CostBreakdown(BaseModel):
    cost_center: CostCenter
    amount: float

