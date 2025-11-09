from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class relativedelta:
    months: int = 0

    def __add__(self, other: date) -> date:
        if isinstance(other, date):
            return _add_months(other, self.months)
        return NotImplemented

    def __radd__(self, other: date) -> date:
        return self.__add__(other)


def _add_months(dt: date, months: int) -> date:
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, _last_day_of_month(year, month))
    return date(year, month, day)


def _last_day_of_month(year: int, month: int) -> int:
    if month in {1, 3, 5, 7, 8, 10, 12}:
        return 31
    if month in {4, 6, 9, 11}:
        return 30
    # February
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        return 29
    return 28

