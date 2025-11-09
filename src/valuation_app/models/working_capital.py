from __future__ import annotations

from pydantic import BaseModel


class WorkingCapitalModel(BaseModel):
    dso: float = 0.0
    dpo: float = 0.0
    dio: float = 0.0
    min_cash_balance: float = 0.0


class WorkingCapitalDelta(BaseModel):
    change_ar: float
    change_ap: float
    change_inventory: float
    total_change: float

