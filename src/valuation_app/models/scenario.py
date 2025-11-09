from __future__ import annotations

from pydantic import BaseModel

from .capex import CapexModel
from .common import CompanyState, CurrencySettings, ScenarioMeta, TimeframeSettings
from .costs import CostModel
from .funding import FundingModel
from .headcount import HeadcountModel
from .revenue import RevenueModel
from .taxes import TaxModel
from .valuation import ValuationSettings
from .working_capital import WorkingCapitalModel


class ScenarioInput(BaseModel):
    meta: ScenarioMeta
    currency: CurrencySettings
    timeframe: TimeframeSettings
    company_state: CompanyState
    revenue: RevenueModel
    headcount: HeadcountModel
    costs: CostModel
    taxes: TaxModel
    capex: CapexModel
    working_capital: WorkingCapitalModel
    funding: FundingModel
    valuation: ValuationSettings

