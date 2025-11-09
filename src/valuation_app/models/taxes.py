from __future__ import annotations

from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field


class TaxBase(str, Enum):
    GROSS_REVENUE = "gross_revenue"
    NET_REVENUE = "net_revenue"
    EBIT = "ebit"
    EBT = "ebt"
    PAYROLL = "payroll"


class TaxRegime(str, Enum):
    SIMPLES = "simples"
    LUCRO_PRESUMIDO = "lucro_presumido"
    LUCRO_REAL = "lucro_real"
    CUSTOM = "custom"


class TaxBracket(BaseModel):
    threshold: float
    rate: float


class TaxComponent(BaseModel):
    name: str
    base: TaxBase
    rate: float
    deductible: bool = False


class ProgressiveTax(BaseModel):
    name: str
    base: TaxBase
    brackets: List[TaxBracket]


class TaxCredit(BaseModel):
    name: str
    base: TaxBase
    rate: float


class TaxModel(BaseModel):
    regime: TaxRegime
    taxes: List[TaxComponent] = Field(default_factory=list)
    progressive: List[ProgressiveTax] = Field(default_factory=list)
    credits: List[TaxCredit] = Field(default_factory=list)
    effective_income_tax_rate: float = 0.0


class TaxBreakdown(BaseModel):
    name: str
    amount: float

