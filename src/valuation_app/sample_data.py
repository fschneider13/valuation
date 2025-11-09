from __future__ import annotations

from datetime import date

from .models.capex import CapexItem, CapexModel
from .models.common import CompanyState, CurrencySettings, ScenarioMeta, TimeframeSettings, MonthlySchedule
from .models.costs import CostAllocation, CostCenter, CostItem, CostModel, CostNature
from .models.funding import EquityRound, FundingModel
from .models.headcount import HeadcountModel, HeadcountPosition, HiringPlan
from .models.revenue import RevenueModel, RevenuePlan
from .models.scenario import ScenarioInput
from .models.taxes import TaxBase, TaxComponent, TaxModel, TaxRegime
from .models.valuation import TerminalValueMethod, ValuationSettings, MultipleMetric
from .models.working_capital import WorkingCapitalModel


def build_sample_scenario() -> ScenarioInput:
    revenue_plan = RevenuePlan(
        name="SaaS",
        initial_customers=120,
        initial_arpa=3200,
        new_customers=MonthlySchedule(default=12.0),
        churn_rate=MonthlySchedule(default=0.015),
        expansion_rate=MonthlySchedule(default=0.03),
        arpa_growth_rate=MonthlySchedule(default=0.015),
    )

    revenue = RevenueModel(
        plans=[revenue_plan],
    )

    headcount = HeadcountModel(
        positions=[
            HeadcountPosition(
                role="Engineer",
                area="Engineering",
                level="Senior",
                current_fte=9,
                base_salary=240000,
                benefits_pct=0.25,
            ),
            HeadcountPosition(
                role="Product Manager",
                area="Product",
                level="Pleno",
                current_fte=3,
                base_salary=210000,
                benefits_pct=0.22,
            ),
            HeadcountPosition(
                role="Sales",
                area="Sales",
                level="Mid",
                current_fte=4,
                base_salary=180000,
                benefits_pct=0.18,
                bonus_pct=0.1,
            ),
            HeadcountPosition(
                role="Customer Success",
                area="CS",
                level="Mid",
                current_fte=3,
                base_salary=156000,
                benefits_pct=0.18,
            ),
            HeadcountPosition(
                role="G&A",
                area="GNA",
                level="Mid",
                current_fte=3,
                base_salary=150000,
                benefits_pct=0.16,
            ),
        ],
        hires=[
            HiringPlan(role="Engineer", month_index=6, quantity=2),
            HiringPlan(role="Sales", month_index=3, quantity=1),
        ],
        attrition_pct=MonthlySchedule(default=0.005),
    )

    costs = CostModel(
        items=[
            CostItem(
                name="Opex Fixo",
                nature=CostNature.FIXED,
                allocation=CostAllocation.OPEX,
                cost_center=CostCenter.GNA,
                base_amount=120000,
            ),
        ],
        cogs_variable_pct=0.16,
    )

    taxes = TaxModel(
        regime=TaxRegime.LUCRO_PRESUMIDO,
        taxes=[
            TaxComponent(name="PIS/COFINS", base=TaxBase.GROSS_REVENUE, rate=0.0365),
            TaxComponent(name="ISS", base=TaxBase.NET_REVENUE, rate=0.03),
        ],
        effective_income_tax_rate=0.24,
    )

    capex = CapexModel(
        items=[
            CapexItem(name="Plataforma", month_index=0, amount=450000, useful_life_months=36),
        ]
    )

    working_capital = WorkingCapitalModel(dso=30, dpo=35, dio=0, min_cash_balance=100000)

    funding = FundingModel(
        equity_rounds=[EquityRound(name="Seed", month_index=0, amount=3000000, post_money_valuation=12000000, dilution_pct=0.2)]
    )

    valuation = ValuationSettings(
        wacc=0.18,
        perpetual_growth_rate=0.03,
        terminal_method=TerminalValueMethod.PERPETUITY,
        terminal_multiple=8.0,
        terminal_multiple_metric=MultipleMetric.EBITDA,
        exit_year_multiple=6.0,
        target_exit_year=5,
        discount_rate_vc=0.35,
        probability_of_success=0.6,
    )

    scenario = ScenarioInput(
        meta=ScenarioMeta(id="sample-base", name="Base"),
        currency=CurrencySettings(base_currency="BRL", display_currency="BRL", fx_rate=1.0),
        timeframe=TimeframeSettings(start_date=date(2024, 1, 1), months=36),
        company_state=CompanyState(
            as_of=date(2023, 12, 31),
            cash=2500000,
            accounts_receivable=100000,
            accounts_payable=90000,
            fixed_assets=450000,
            accumulated_depreciation=0,
            debt=0,
            equity=5000000,
        ),
        revenue=revenue,
        headcount=headcount,
        costs=costs,
        taxes=taxes,
        capex=capex,
        working_capital=working_capital,
        funding=funding,
        valuation=valuation,
    )
    return scenario

