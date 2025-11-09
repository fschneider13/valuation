from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel


class DebtType(str, Enum):
    TERM = "term"
    REVOLVER = "revolver"


class EquityRound(BaseModel):
    name: str
    month_index: int
    amount: float
    post_money_valuation: float
    dilution_pct: float


class DebtInstrument(BaseModel):
    name: str
    month_index: int
    amount: float
    interest_rate_annual: float
    term_months: int
    debt_type: DebtType = DebtType.TERM
    grace_period_months: int = 0


class FundingModel(BaseModel):
    equity_rounds: List[EquityRound] = []
    debt: List[DebtInstrument] = []


class CapitalStructureSnapshot(BaseModel):
    equity_value: float
    debt_outstanding: float
    option_pool_pct: float = 0.0

