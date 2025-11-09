from __future__ import annotations

from valuation_app.sample_data import build_sample_scenario
from valuation_app.services.calculator import ScenarioCalculator


def test_sample_scenario_generates_results():
    scenario = build_sample_scenario()
    calculator = ScenarioCalculator()
    result = calculator.run(scenario)

    assert len(result.monthly) == scenario.timeframe.months
    assert result.monthly[0].income_statement.net_revenue > 0
    assert result.monthly[-1].balance_sheet.cash > 0
    assert result.valuation.dcf.enterprise_value > 0
    assert result.valuation.vc_method.exit_value > 0


