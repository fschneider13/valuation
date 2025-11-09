# Startup Valuation Engine

This project provides a financial modeling and valuation engine tailored for high-growth startups. It models monthly projections, aggregates annual statements, and supports valuation methodologies such as DCF, market multiples, and VC method. The backend is powered by FastAPI with a modular calculation engine that can be extended for additional scenarios or reporting layers.

## Features

- Scenario-based financial projections with configurable horizons.
- Revenue modeling for subscription businesses with churn, expansion, and deferral logic.
- Headcount planning including hires, attrition, and per-area cost breakdowns.
- Cost modeling for fixed, variable, and supplier-based contracts.
- Calculation of full financial statements (Income Statement, Balance Sheet, Cash Flow).
- Working capital management and free cash flow computation (FCFF/FCFE).
- Valuation toolkit covering DCF, terminal value alternatives, multiples, and VC method.
- Dashboard-ready slices for revenue, cash, valuation, and unit economics trends.
- FastAPI endpoints for creating, running, and comparing scenarios.

## Getting Started

1. **Install dependencies**

   ```bash
   pip install -e .[dev]
   ```

2. **Run tests**

   ```bash
   pytest
   ```

3. **Start the API**

   ```bash
   uvicorn valuation_app.main:app --reload
   ```

4. **Seed with sample scenario**

   ```python
   from valuation_app.sample_data import build_sample_scenario
   from valuation_app.main import SCENARIOS

   SCENARIOS.clear()
   SCENARIOS["sample-base"] = build_sample_scenario()
   ```

The API now exposes endpoints under `http://localhost:8000` where you can run the sample scenario (`POST /run`) or inspect projections (`GET /scenarios/sample-base`).

## Project Structure

- `src/valuation_app/models/`: Pydantic models encapsulating scenario inputs and outputs.
- `src/valuation_app/services/calculator.py`: Core financial engine that loops through monthly periods to assemble statements, working capital, and valuation outputs.
- `src/valuation_app/main.py`: FastAPI application exposing CRUD and execution endpoints for scenarios.
- `src/valuation_app/sample_data.py`: Seed data aligned with the provided SaaS startup example.
- `tests/`: Automated tests ensuring the engine produces consistent outputs for the sample scenario.

## Extending the Engine

The calculation service is built to be composable. Key extension points include:

- Adding new revenue streams or drivers by extending `RevenuePlan`.
- Customizing tax regimes by injecting additional `TaxComponent` or progressive rules.
- Extending dashboards by updating `_build_dashboards` within the calculator service.
- Integrating persistence by replacing the in-memory `SCENARIOS` registry with a database-backed repository.

Pull requests and suggestions are welcome!

