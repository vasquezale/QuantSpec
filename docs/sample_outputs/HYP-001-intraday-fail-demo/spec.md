---
hypothesis_id: HYP-001-intraday-fail-demo
spec_version: 1
generated_by: live
prompts_version: 1.0.0
prompt_hash: sha256:48472a0ce3bce250d688d190aaf5535c79bb8fa366ca18c8bcbdf9b59243f67e
brief_hash: sha256:25b7841b5d3a8f687a54649a32cc89a57a1b7020a46fe8085bcb7c7cde02bb5f
strategy:
  name: intraday_breakout_demo
  params:
    entry_rule: fixture_breakout
    risk_per_trade_pct: 0.5
---

# Strategy Specification: HYP-001-intraday-fail-demo

## Entry Conditions

- Market: DEMO_INTRADAY synthetic asset
- Timeframe: 15-minute bars (DEMO_M15)
- Direction: Long and short positions permitted
- Breakout detection: Price movement beyond a defined threshold within the intraday session
- Session constraints: Positions may only be opened during active intraday hours
- Maximum entries: 1 trade per calendar day
- Pre-entry validation: Confirm sufficient margin and risk budget availability before order placement

## Exit Conditions

- Mandatory stop-loss: All positions must have a stop-loss order active
- Intraday closure: All open positions must be closed before end of trading day
- Time-based exit: If no other exit condition triggers, close at session end
- Stop-loss exit: Position closed when price reaches predefined stop level
- Target exit: Optional profit target may be defined per trade
- Manual override: Position may be closed early if risk parameters are breached

## Risk Parameters

- Maximum daily risk exposure: 5.0% of account equity
- Risk per individual trade: 0.5% of account equity
- Maximum trades per day: 1
- Position sizing: Calculated to respect per-trade risk limit given stop-loss distance
- Stop-loss requirement: Mandatory on all positions, no exceptions
- Intraday-only constraint: No overnight or multi-day positions permitted
- Pip size: 0.01 for position and risk calculations

## Validation Requirements

- Data source: Fixture data located at `quant_spec/data/fixtures/HYP-001-intraday-fail-demo/trades.csv`
- In-sample period: 2020-01-01 to 2020-12-31
- Out-of-sample period: 2021-01-01 to 2021-12-31
- Reproducibility: All evaluations must use identical fixture data
- Quality gates: Strategy must pass defined quality thresholds on both in-sample and out-of-sample periods
- Gate failure protocol: If quality gates are not met, hypothesis is closed with "insufficient evidence" outcome
- Trade log validation: All trades must comply with stated entry, exit, and risk parameters

## Assumptions

- Synthetic demonstration data represents simplified market conditions
- Fixture data is static and reproducible across all evaluation runs
- Breakout signals can be reliably identified in 15-minute timeframe
- Stop-loss orders execute at specified prices without slippage (synthetic environment)
- Intraday session boundaries are clearly defined and enforced
- Account equity is available for position sizing calculations
- Single-asset focus: No portfolio or correlation considerations
- No transaction costs, spreads, or commissions included in synthetic evaluation

## Known Risks

- **Designed-to-fail scenario**: This demonstration is explicitly constructed to fail quality gate evaluation
- **Synthetic data limitations**: Fixture data does not reflect real market dynamics, volatility clustering, or regime changes
- **Overfitting potential**: Any pattern identified in fixed synthetic data will not generalize
- **No execution modeling**: Real-world slippage, partial fills, and requotes are not represented
- **Single-trade-per-day constraint**: May miss valid signals or force suboptimal trade selection
- **Session-end forced closure**: Mandatory intraday exit may realize unnecessary losses
- **Static risk parameters**: Fixed percentage risk may not adapt to changing market conditions
- **Quality gate failure expected**: Hypothesis closure anticipated due to weak evidence in fixture data
- **No live market applicability**: Results cannot be extrapolated to real trading conditions
