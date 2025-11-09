from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Tuple

from dateutil.relativedelta import relativedelta

from ..models.capex import CapexItem
from ..models.costs import (
    CostAllocation,
    CostBreakdown,
    CostModel,
    CostNature,
    CostCenter,
    SupplierContract,
)
from ..models.headcount import HeadcountCostBreakdown, HeadcountModel, HeadcountPosition, HiringPlan
from ..models.revenue import RevenueModel, RevenueSummary
from ..models.results import (
    AnnualSummary,
    BalanceSheet,
    CashFlowStatement,
    IncomeStatement,
    MonthlyProjection,
    ScenarioResult,
)
from ..models.scenario import ScenarioInput
from ..models.taxes import TaxBase, TaxBreakdown, TaxComponent, TaxModel
from ..models.valuation import MultipleMetric, MultipleValuationResult, TerminalValueMethod, ValuationResult, DiscountedCashFlowResult, VCValuationResult, ScorecardValuationResult
from ..models.working_capital import WorkingCapitalDelta
from ..models.valuation import ValuationSettings


@dataclass
class PlanState:
    active_customers: float
    deferred_revenue: Deque[float]


@dataclass
class HeadcountState:
    position: HeadcountPosition
    fte: float
    current_salary: float


@dataclass
class DebtState:
    name: str
    outstanding: float
    interest_rate: float
    term_months: int
    remaining_term: int
    grace_months: int


class ScenarioCalculator:
    def run(self, scenario: ScenarioInput) -> ScenarioResult:
        months = scenario.timeframe.months
        start_date = scenario.timeframe.start_date
        plan_states = {plan.name: PlanState(plan.initial_customers, deque([0.0] * plan.revenue_deferral_months)) for plan in scenario.revenue.plans}
        headcount_states = {pos.role: HeadcountState(pos, pos.current_fte, pos.base_salary) for pos in scenario.headcount.positions}
        hiring_lookup = defaultdict(list)
        for hire in scenario.headcount.hires:
            hiring_lookup[hire.month_index].append(hire)

        capex_schedule: List[Tuple[int, CapexItem]] = [(item.month_index, item) for item in scenario.capex.items]
        debt_states: List[DebtState] = []

        company_state = scenario.company_state
        cash = company_state.cash
        accounts_receivable = company_state.accounts_receivable
        accounts_payable = company_state.accounts_payable
        inventory = company_state.inventory
        fixed_assets = company_state.fixed_assets
        accumulated_depreciation = company_state.accumulated_depreciation
        debt_balance = company_state.debt
        equity = company_state.equity or (company_state.cash + company_state.net_fixed_assets())

        depreciation_tracks: List[Tuple[int, float, float]] = []  # (remaining_months, amount, salvage)

        monthly_results: List[MonthlyProjection] = []

        previous_year = None
        annual_accumulators: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        annual_cash: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for month_index in range(months):
            period_start = start_date + relativedelta(months=month_index)
            revenue_summary = self._compute_revenue(
                month_index,
                scenario.revenue,
                plan_states,
            )

            headcount_breakdown, payroll_total = self._compute_headcount(
                month_index,
                scenario.headcount,
                headcount_states,
                hiring_lookup,
            )

            cost_breakdown, total_cogs, total_opex = self._compute_costs(
                month_index,
                scenario.costs,
                revenue_summary,
            )

            total_cogs += scenario.costs.cogs_per_customer * sum(state.active_customers for state in plan_states.values())
            total_cogs += scenario.costs.cogs_variable_pct * revenue_summary.total_net

            revenue_taxes_amount, tax_breakdown_components = self._compute_revenue_taxes(
                revenue_summary,
                scenario.taxes,
                payroll_total,
            )

            gross_revenue = revenue_summary.total_gross
            net_revenue = revenue_summary.total_net - revenue_taxes_amount

            gross_margin = net_revenue - total_cogs
            operating_expenses = total_opex + payroll_total
            ebitda = gross_margin - operating_expenses

            depreciation, accumulated_depreciation, fixed_assets = self._compute_depreciation(
                month_index,
                capex_schedule,
                depreciation_tracks,
                fixed_assets,
                accumulated_depreciation,
            )

            amortization = 0.0
            ebit = ebitda - depreciation - amortization

            interest_expense, principal_paid = self._compute_debt(
                month_index,
                scenario.funding,
                debt_states,
                debt_balance,
            )
            debt_balance += sum(new_debt.amount for new_debt in scenario.funding.debt if new_debt.month_index == month_index)
            debt_balance -= principal_paid

            ebt = ebit - interest_expense
            income_tax = max(0.0, ebt) * scenario.taxes.effective_income_tax_rate
            net_income = ebt - income_tax

            working_capital_delta = self._compute_working_capital(
                scenario.working_capital,
                net_revenue,
                total_cogs + operating_expenses,
                revenue_summary,
                accounts_receivable,
                accounts_payable,
                inventory,
            )
            accounts_receivable += working_capital_delta.change_ar
            accounts_payable += working_capital_delta.change_ap
            inventory += working_capital_delta.change_inventory

            capex_amount = sum(item.amount for idx, item in capex_schedule if idx == month_index)

            operating_cash_flow = net_income + depreciation + amortization - working_capital_delta.total_change
            investing_cash_flow = -capex_amount

            equity_raise, debt_inflows = self._funding_inflows(month_index, scenario.funding)
            financing_cash_flow = equity_raise + debt_inflows - principal_paid - interest_expense

            fcff = ebit * (1 - scenario.taxes.effective_income_tax_rate) + depreciation + amortization - working_capital_delta.total_change - capex_amount
            fcfe = fcff - principal_paid + debt_inflows

            net_change_in_cash = operating_cash_flow + investing_cash_flow + financing_cash_flow
            cash += net_change_in_cash
            if cash < scenario.working_capital.min_cash_balance:
                shortfall = scenario.working_capital.min_cash_balance - cash
                cash += shortfall
                financing_cash_flow += shortfall
                equity += shortfall

            equity += net_income + equity_raise

            income_statement = IncomeStatement(
                gross_revenue=gross_revenue,
                revenue_taxes=revenue_taxes_amount,
                net_revenue=net_revenue,
                cogs=total_cogs,
                gross_margin=gross_margin,
                operating_expenses=operating_expenses,
                ebitda=ebitda,
                depreciation=depreciation,
                amortization=amortization,
                ebit=ebit,
                interest=interest_expense,
                ebt=ebt,
                income_tax=income_tax,
                net_income=net_income,
            )

            balance_sheet = BalanceSheet(
                cash=cash,
                accounts_receivable=accounts_receivable,
                inventory=inventory,
                fixed_assets=fixed_assets,
                accumulated_depreciation=accumulated_depreciation,
                accounts_payable=accounts_payable,
                debt=debt_balance,
                equity=equity,
            )

            cash_flow = CashFlowStatement(
                operating_cash_flow=operating_cash_flow,
                investing_cash_flow=investing_cash_flow,
                financing_cash_flow=financing_cash_flow,
                net_change_in_cash=net_change_in_cash,
                ending_cash=cash,
                fcff=fcff,
                fcfe=fcfe,
            )

            monthly_results.append(
                MonthlyProjection(
                    period_start=period_start,
                    income_statement=income_statement,
                    balance_sheet=balance_sheet,
                    cash_flow=cash_flow,
                    revenue_summary=revenue_summary,
                    headcount_breakdown=headcount_breakdown,
                    cost_breakdown=cost_breakdown,
                    tax_breakdown=tax_breakdown_components,
                    working_capital_delta=working_capital_delta,
                )
            )

            self._accumulate_annual(period_start, income_statement, cash_flow, annual_accumulators, annual_cash)

        annual_summaries = self._build_annual_summaries(annual_accumulators, annual_cash)
        valuation = self._build_valuation(monthly_results, annual_summaries, scenario)
        dashboards = self._build_dashboards(monthly_results, annual_summaries, valuation)

        return ScenarioResult(monthly=monthly_results, annual=annual_summaries, valuation=valuation, dashboards=dashboards)

    def _compute_revenue(
        self,
        month_index: int,
        revenue_model: RevenueModel,
        plan_states: Dict[str, PlanState],
    ) -> RevenueSummary:
        total_gross = 0.0
        total_net = 0.0
        total_churn = 0.0
        total_expansion = 0.0
        arr = 0.0
        for plan in revenue_model.plans:
            state = plan_states[plan.name]
            new_customers = max(0.0, plan.new_customers.value_for(month_index))
            churn_rate = plan.churn_rate.value_for(month_index)
            expansion_rate = plan.expansion_rate.value_for(month_index)
            contraction_rate = plan.contraction_rate.value_for(month_index)
            arpa_growth = plan.arpa_growth_rate.value_for(month_index)
            seasonal_factor = plan.seasonal_pattern.factor(month_index)

            churned_customers = state.active_customers * churn_rate
            state.active_customers = max(0.0, state.active_customers + new_customers - churned_customers)
            arpa = plan.initial_arpa * (1 + arpa_growth) ** (month_index + 1)
            arpa *= seasonal_factor
            base_revenue = state.active_customers * arpa
            discount = base_revenue * plan.discount_rate.value_for(month_index)
            expansion_revenue = base_revenue * expansion_rate
            contraction_revenue = base_revenue * contraction_rate
            gross_revenue = base_revenue + expansion_revenue - contraction_revenue
            services_revenue = plan.services_attach_rate * new_customers * plan.services_asp
            transactional_revenue = plan.transactional_volume.value_for(month_index) * plan.transactional_fee
            gross_revenue += services_revenue + transactional_revenue

            if plan.revenue_deferral_months > 0:
                state.deferred_revenue.append(gross_revenue)
                recognized = state.deferred_revenue.popleft() / max(1, plan.revenue_deferral_months)
            else:
                recognized = gross_revenue

            total_gross += gross_revenue
            total_net += recognized - discount
            total_churn += churned_customers * arpa
            total_expansion += expansion_revenue
            arr += recognized * 12
        total_gross += revenue_model.professional_services_revenue.value_for(month_index)
        total_net += revenue_model.other_recurring_revenue.value_for(month_index)

        revenue_summary = RevenueSummary(
            total_gross=total_gross,
            total_net=total_net,
            total_churn=total_churn,
            total_expansion=total_expansion,
            arr=arr,
        )
        return revenue_summary

    def _compute_headcount(
        self,
        month_index: int,
        headcount_model: HeadcountModel,
        headcount_states: Dict[str, HeadcountState],
        hiring_lookup: Dict[int, List[HiringPlan]],
    ) -> Tuple[List[HeadcountCostBreakdown], float]:
        area_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for hire in hiring_lookup.get(month_index, []):
            if hire.role not in headcount_states:
                matching = next((pos for pos in headcount_model.positions if pos.role == hire.role), None)
                if matching is None:
                    continue
                headcount_states[hire.role] = HeadcountState(matching, 0.0, matching.base_salary)
            state = headcount_states[hire.role]
            state.fte += hire.quantity
            if hire.salary_override:
                state.current_salary = hire.salary_override

        attrition_rate = headcount_model.attrition_pct.value_for(month_index)
        payroll_total = 0.0
        breakdown: List[HeadcountCostBreakdown] = []

        for state in headcount_states.values():
            if state.fte <= 0:
                continue
            state.fte *= (1 - attrition_rate)
            monthly_salary = state.current_salary / 12
            salary_cost = state.fte * monthly_salary
            benefits = salary_cost * state.position.benefits_pct + state.fte * state.position.benefits_fixed
            bonus = salary_cost * state.position.bonus_pct
            payroll_taxes = salary_cost * state.position.payroll_taxes_pct
            subs_cost = sum(sub.monthly_cost * (1 + sub.price_adjustment.factor_for_month(month_index)) for sub in state.position.subscriptions) * state.fte
            total = salary_cost + benefits + bonus + payroll_taxes + subs_cost
            payroll_total += total
            area_data = area_totals[state.position.area]
            area_data["salaries"] += salary_cost
            area_data["benefits"] += benefits + bonus + payroll_taxes
            area_data["subscriptions"] += subs_cost
            area_data["total"] += total
            area_data["fte"] += state.fte

        for area, metrics in area_totals.items():
            breakdown.append(
                HeadcountCostBreakdown(
                    area=area,
                    salaries=metrics["salaries"],
                    benefits=metrics["benefits"],
                    subscriptions=metrics["subscriptions"],
                    total=metrics["total"],
                    fte=metrics["fte"],
                )
            )
        return breakdown, payroll_total

    def _compute_costs(
        self,
        month_index: int,
        cost_model: CostModel,
        revenue_summary: RevenueSummary,
    ) -> Tuple[List[CostBreakdown], float, float]:
        breakdown: Dict[CostCenter, float] = defaultdict(float)
        cogs_total = 0.0
        opex_total = 0.0
        for item in cost_model.items:
            base_amount = item.base_amount
            if item.nature == CostNature.VARIABLE:
                driver_value = revenue_summary.total_net if item.driver == "revenue" else revenue_summary.total_gross
                base_amount = driver_value * item.variable_rate
            amount = base_amount * item.schedule.value_for(month_index)
            amount *= 1 + item.price_adjustment.factor_for_month(month_index)
            breakdown[item.cost_center] += amount
            if item.allocation == CostAllocation.COGS:
                cogs_total += amount
            else:
                opex_total += amount
        for contract in cost_model.supplier_contracts:
            if month_index < contract.start_month:
                continue
            escalations = max(0, (month_index - contract.start_month) // contract.escalation_frequency_months)
            amount = contract.base_amount * ((1 + contract.escalation_pct) ** escalations)
            breakdown[contract.cost_center] += amount
            if contract.allocation == CostAllocation.COGS:
                cogs_total += amount
            else:
                opex_total += amount
        breakdown_list = [CostBreakdown(cost_center=center, amount=value) for center, value in breakdown.items()]
        return breakdown_list, cogs_total, opex_total

    def _compute_revenue_taxes(
        self,
        revenue_summary: RevenueSummary,
        tax_model: TaxModel,
        payroll_total: float,
    ) -> Tuple[float, List[TaxBreakdown]]:
        tax_amount = 0.0
        breakdown: List[TaxBreakdown] = []
        base_values = {
            TaxBase.GROSS_REVENUE: revenue_summary.total_gross,
            TaxBase.NET_REVENUE: revenue_summary.total_net,
            TaxBase.PAYROLL: payroll_total,
        }
        for tax in tax_model.taxes:
            base = base_values.get(tax.base, revenue_summary.total_net)
            amount = base * tax.rate
            breakdown.append(TaxBreakdown(name=tax.name, amount=amount))
            if tax.base in {TaxBase.GROSS_REVENUE, TaxBase.NET_REVENUE}:
                tax_amount += amount
        return tax_amount, breakdown

    def _compute_depreciation(
        self,
        month_index: int,
        capex_schedule: List[Tuple[int, CapexItem]],
        depreciation_tracks: List[Tuple[int, float, float]],
        fixed_assets: float,
        accumulated_depreciation: float,
    ) -> Tuple[float, float, float]:
        for idx, item in capex_schedule:
            if idx == month_index:
                fixed_assets += item.amount
                depreciation_tracks.append((item.useful_life_months, item.amount, item.salvage_value))
        depreciation = 0.0
        updated_tracks: List[Tuple[int, float, float]] = []
        for remaining, amount, salvage in depreciation_tracks:
            if remaining <= 0:
                continue
            monthly_dep = max(0.0, (amount - salvage) / remaining)
            depreciation += monthly_dep
            updated_tracks.append((remaining - 1, amount, salvage))
        accumulated_depreciation += depreciation
        depreciation_tracks.clear()
        depreciation_tracks.extend(updated_tracks)
        return depreciation, accumulated_depreciation, fixed_assets

    def _compute_debt(
        self,
        month_index: int,
        funding_model,
        debt_states: List[DebtState],
        starting_debt_balance: float,
    ) -> Tuple[float, float]:
        interest_expense = 0.0
        principal_paid = 0.0
        for instrument in funding_model.debt:
            if instrument.month_index == month_index:
                debt_states.append(
                    DebtState(
                        name=instrument.name,
                        outstanding=instrument.amount,
                        interest_rate=instrument.interest_rate_annual,
                        term_months=instrument.term_months,
                        remaining_term=instrument.term_months,
                        grace_months=instrument.grace_period_months,
                    )
                )
        updated_states: List[DebtState] = []
        for state in debt_states:
            if state.outstanding <= 0:
                continue
            interest = state.outstanding * (state.interest_rate / 12)
            interest_expense += interest
            if state.grace_months > 0:
                state.grace_months -= 1
                updated_states.append(state)
                continue
            if state.remaining_term > 0:
                principal_payment = state.outstanding / state.remaining_term
            else:
                principal_payment = state.outstanding
            principal_payment = min(principal_payment, state.outstanding)
            principal_paid += principal_payment
            state.outstanding -= principal_payment
            state.remaining_term = max(0, state.remaining_term - 1)
            if state.outstanding > 1e-6:
                updated_states.append(state)
        debt_states.clear()
        debt_states.extend(updated_states)
        return interest_expense, principal_paid

    def _compute_working_capital(
        self,
        wc_model,
        net_revenue: float,
        cost_base: float,
        revenue_summary: RevenueSummary,
        previous_ar: float,
        previous_ap: float,
        previous_inventory: float,
    ) -> WorkingCapitalDelta:
        target_ar = net_revenue * (wc_model.dso / 30)
        target_ap = cost_base * (wc_model.dpo / 30)
        target_inventory = revenue_summary.total_gross * (wc_model.dio / 30)
        change_ar = target_ar - previous_ar
        change_ap = target_ap - previous_ap
        change_inventory = target_inventory - previous_inventory
        total_change = change_ar - change_ap + change_inventory
        return WorkingCapitalDelta(
            change_ar=change_ar,
            change_ap=change_ap,
            change_inventory=change_inventory,
            total_change=total_change,
        )

    def _funding_inflows(self, month_index: int, funding_model) -> Tuple[float, float]:
        equity = sum(round.amount for round in funding_model.equity_rounds if round.month_index == month_index)
        debt = sum(instrument.amount for instrument in funding_model.debt if instrument.month_index == month_index)
        return equity, debt

    def _accumulate_annual(
        self,
        period_start: date,
        income_statement: IncomeStatement,
        cash_flow: CashFlowStatement,
        accumulators: Dict[int, Dict[str, float]],
        cash_accumulators: Dict[int, Dict[str, float]],
    ) -> None:
        year = period_start.year
        acc = accumulators[year]
        acc["gross_revenue"] += income_statement.gross_revenue
        acc["revenue_taxes"] += income_statement.revenue_taxes
        acc["net_revenue"] += income_statement.net_revenue
        acc["cogs"] += income_statement.cogs
        acc["operating_expenses"] += income_statement.operating_expenses
        acc["ebitda"] += income_statement.ebitda
        acc["depreciation"] += income_statement.depreciation
        acc["amortization"] += income_statement.amortization
        acc["ebit"] += income_statement.ebit
        acc["interest"] += income_statement.interest
        acc["ebt"] += income_statement.ebt
        acc["income_tax"] += income_statement.income_tax
        acc["net_income"] += income_statement.net_income

        cash_acc = cash_accumulators[year]
        cash_acc["operating"] += cash_flow.operating_cash_flow
        cash_acc["investing"] += cash_flow.investing_cash_flow
        cash_acc["financing"] += cash_flow.financing_cash_flow
        cash_acc["fcff"] += cash_flow.fcff
        cash_acc["fcfe"] += cash_flow.fcfe

    def _build_annual_summaries(
        self,
        accumulators: Dict[int, Dict[str, float]],
        cash_accumulators: Dict[int, Dict[str, float]],
    ) -> List[AnnualSummary]:
        summaries: List[AnnualSummary] = []
        for year in sorted(accumulators.keys()):
            acc = accumulators[year]
            cash_acc = cash_accumulators[year]
            income = IncomeStatement(
                gross_revenue=acc["gross_revenue"],
                revenue_taxes=acc["revenue_taxes"],
                net_revenue=acc["net_revenue"],
                cogs=acc["cogs"],
                gross_margin=acc["net_revenue"] - acc["cogs"],
                operating_expenses=acc["operating_expenses"],
                ebitda=acc["ebitda"],
                depreciation=acc["depreciation"],
                amortization=acc["amortization"],
                ebit=acc["ebit"],
                interest=acc["interest"],
                ebt=acc["ebt"],
                income_tax=acc["income_tax"],
                net_income=acc["net_income"],
            )
            cash_flow = CashFlowStatement(
                operating_cash_flow=cash_acc["operating"],
                investing_cash_flow=cash_acc["investing"],
                financing_cash_flow=cash_acc["financing"],
                net_change_in_cash=cash_acc["operating"] + cash_acc["investing"] + cash_acc["financing"],
                ending_cash=0.0,
                fcff=cash_acc["fcff"],
                fcfe=cash_acc["fcfe"],
            )
            summaries.append(AnnualSummary(year=year, income_statement=income, cash_flow=cash_flow))
        return summaries

    def _build_valuation(
        self,
        monthly_results: List[MonthlyProjection],
        annual_summaries: List[AnnualSummary],
        scenario: ScenarioInput,
    ) -> ValuationResult:
        cash_flows = [month.cash_flow.fcff for month in monthly_results]
        valuation_settings = scenario.valuation
        wacc = valuation_settings.wacc
        discount_factors = [(1 + wacc) ** (i / 12) for i in range(1, len(cash_flows) + 1)]
        pv_cash_flows = sum(cf / df for cf, df in zip(cash_flows, discount_factors))
        terminal_value = self._compute_terminal_value(valuation_settings, annual_summaries)
        pv_terminal = terminal_value / ((1 + wacc) ** (len(cash_flows) / 12))
        enterprise_value = pv_cash_flows + pv_terminal
        last_balance = monthly_results[-1].balance_sheet
        equity_value = enterprise_value - last_balance.debt + last_balance.cash

        dcf_result = DiscountedCashFlowResult(
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            pv_of_cash_flows=pv_cash_flows,
            pv_of_terminal_value=pv_terminal,
            terminal_value=terminal_value,
            discount_factors=discount_factors,
        )

        multiples = self._compute_multiples(valuation_settings, annual_summaries)
        vc_method = self._compute_vc_method(valuation_settings, scenario.funding, annual_summaries)
        scorecard = self._compute_scorecard(valuation_settings, equity_value)

        return ValuationResult(dcf=dcf_result, multiples=multiples, vc_method=vc_method, scorecard=scorecard)

    def _compute_terminal_value(
        self,
        valuation_settings: ValuationSettings,
        annual_summaries: List[AnnualSummary],
    ) -> float:
        if not annual_summaries:
            return 0.0
        last = annual_summaries[-1]
        if valuation_settings.terminal_method == TerminalValueMethod.PERPETUITY:
            fcff = last.cash_flow.fcff / 12
            terminal = (fcff * (1 + valuation_settings.perpetual_growth_rate)) / (valuation_settings.wacc - valuation_settings.perpetual_growth_rate)
            return terminal
        metric_map = {
            MultipleMetric.EBITDA: last.income_statement.ebitda,
            MultipleMetric.REVENUE: last.income_statement.net_revenue,
            MultipleMetric.ARR: last.income_statement.net_revenue,
        }
        metric_value = metric_map.get(valuation_settings.terminal_multiple_metric, last.income_statement.ebitda)
        return metric_value * valuation_settings.terminal_multiple

    def _compute_multiples(
        self,
        valuation_settings: ValuationSettings,
        annual_summaries: List[AnnualSummary],
    ) -> List[MultipleValuationResult]:
        results: List[MultipleValuationResult] = []
        if not annual_summaries:
            return results
        last = annual_summaries[-1]
        metrics = {
            MultipleMetric.EBITDA: last.income_statement.ebitda,
            MultipleMetric.REVENUE: last.income_statement.net_revenue,
            MultipleMetric.ARR: last.income_statement.net_revenue,
        }
        for metric, value in metrics.items():
            multiple = valuation_settings.terminal_multiple if metric == valuation_settings.terminal_multiple_metric else valuation_settings.exit_year_multiple or valuation_settings.terminal_multiple
            results.append(MultipleValuationResult(metric=metric, multiple=multiple, value=value * multiple))
        return results

    def _compute_vc_method(
        self,
        valuation_settings: ValuationSettings,
        funding_model,
        annual_summaries: List[AnnualSummary],
    ) -> VCValuationResult:
        if not annual_summaries:
            return VCValuationResult(exit_value=0.0, ownership_required=0.0, post_money=0.0, pre_money=0.0)
        last = annual_summaries[-1]
        exit_metric = last.income_statement.net_revenue
        exit_value = exit_metric * valuation_settings.exit_year_multiple
        discounted_exit = exit_value / ((1 + valuation_settings.discount_rate_vc) ** valuation_settings.target_exit_year)
        investment = sum(round.amount for round in funding_model.equity_rounds)
        required_ownership = investment / (discounted_exit * valuation_settings.probability_of_success) if discounted_exit else 0.0
        post_money = investment / max(required_ownership, 1e-6) if required_ownership else exit_value
        pre_money = post_money - investment
        return VCValuationResult(
            exit_value=exit_value,
            ownership_required=min(1.0, required_ownership),
            post_money=post_money,
            pre_money=pre_money,
        )

    def _compute_scorecard(self, valuation_settings: ValuationSettings, base_equity: float) -> ScorecardValuationResult | None:
        if not valuation_settings.scorecard_weights:
            return None
        total_weight = sum(valuation_settings.scorecard_weights.values())
        normalized = {k: v / total_weight for k, v in valuation_settings.scorecard_weights.items()}
        score = sum(normalized.values())
        valuation = base_equity * score
        return ScorecardValuationResult(total_score=score, valuation=valuation)

    def _build_dashboards(
        self,
        monthly_results: List[MonthlyProjection],
        annual_summaries: List[AnnualSummary],
        valuation: ValuationResult,
    ) -> List[dict]:
        revenue_trend = {
            "months": [m.period_start.isoformat() for m in monthly_results],
            "net_revenue": [m.income_statement.net_revenue for m in monthly_results],
            "ebitda": [m.income_statement.ebitda for m in monthly_results],
        }
        cash_trend = {
            "months": [m.period_start.isoformat() for m in monthly_results],
            "cash": [m.balance_sheet.cash for m in monthly_results],
            "fcff": [m.cash_flow.fcff for m in monthly_results],
        }
        valuation_slice = {
            "enterprise_value": valuation.dcf.enterprise_value,
            "equity_value": valuation.dcf.equity_value,
            "pv_cash_flows": valuation.dcf.pv_of_cash_flows,
            "pv_terminal": valuation.dcf.pv_of_terminal_value,
        }
        unit_economics = {
            "gross_margin_pct": [
                (m.income_statement.gross_margin / m.income_statement.net_revenue) if m.income_statement.net_revenue else 0.0
                for m in monthly_results
            ],
            "burn_rate": [-(m.cash_flow.operating_cash_flow + m.cash_flow.investing_cash_flow) for m in monthly_results],
        }
        dashboards = [
            {"name": "revenue", "data": revenue_trend},
            {"name": "cash", "data": cash_trend},
            {"name": "valuation", "data": valuation_slice},
            {"name": "unit_economics", "data": unit_economics},
        ]
        return dashboards

