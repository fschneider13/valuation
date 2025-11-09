from __future__ import annotations

from typing import List

from pydantic import BaseModel


class CapexItem(BaseModel):
    name: str
    month_index: int
    amount: float
    useful_life_months: int
    salvage_value: float = 0.0


class CapexModel(BaseModel):
    items: List[CapexItem]


class DepreciationSchedule(BaseModel):
    name: str
    depreciation: float
    net_book_value: float

