from __future__ import annotations

from datetime import date
from typing import Dict, List

from pydantic import BaseModel

from .costs import CostBreakdown
from .headcount import HeadcountCostBreakdown
from .revenue import RevenueSummary
from .taxes import TaxBreakdown
from .valuation import ValuationResult
from .working_capital import WorkingCapitalDelta


class IncomeStatement(BaseModel):
    gross_revenue: float
    revenue_taxes: float
    net_revenue: float
    cogs: float
    gross_margin: float
    operating_expenses: float
    ebitda: float
    depreciation: float
    amortization: float
    ebit: float
    interest: float
    ebt: float
    income_tax: float
    net_income: float


class BalanceSheet(BaseModel):
    cash: float
    accounts_receivable: float
    inventory: float
    fixed_assets: float
    accumulated_depreciation: float
    accounts_payable: float
    debt: float
    equity: float


class CashFlowStatement(BaseModel):
    operating_cash_flow: float
    investing_cash_flow: float
    financing_cash_flow: float
    net_change_in_cash: float
    ending_cash: float
    fcff: float
    fcfe: float


class MonthlyProjection(BaseModel):
    period_start: date
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow: CashFlowStatement
    revenue_summary: RevenueSummary
    headcount_breakdown: List[HeadcountCostBreakdown]
    cost_breakdown: List[CostBreakdown]
    tax_breakdown: List[TaxBreakdown]
    working_capital_delta: WorkingCapitalDelta


class AnnualSummary(BaseModel):
    year: int
    income_statement: IncomeStatement
    cash_flow: CashFlowStatement


class DashboardSlice(BaseModel):
    name: str
    data: Dict[str, float | list | dict]


class ScenarioResult(BaseModel):
    monthly: List[MonthlyProjection]
    annual: List[AnnualSummary]
    valuation: ValuationResult
    dashboards: List[DashboardSlice]

