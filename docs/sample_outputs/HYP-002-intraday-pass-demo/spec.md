---
hypothesis_id: HYP-002-intraday-pass-demo
spec_version: 1
generated_by: fixture
prompts_version: 1.0.0
prompt_hash: sha256:48472a0ce3bce250d688d190aaf5535c79bb8fa366ca18c8bcbdf9b59243f67e
brief_hash: sha256:98be7ba29bf0cfb8fad6b53fe48507f8c91d35b9ab872b5dc9aa09adc2422155
strategy:
  name: intraday_breakout_demo
  params:
    entry_rule: fixture_breakout
    risk_per_trade_pct: 0.5
---

## Entry Conditions

Open one synthetic breakout trade when the fixture signal is active during the demo intraday window.

## Exit Conditions

Close the position inside the same session using the fixture close event. No overnight holding is allowed.

## Risk Parameters

Use one trade per day, require a stop loss, and apply the risk limits declared in the brief.

## Validation Requirements

Evaluate the trade fixture separately for in-sample and out-of-sample windows. Persist results before quality gates are evaluated.

## Assumptions

The fixture data is synthetic and exists only to exercise the validation pipeline.

## Known Risks

Passing gates only marks the hypothesis as ready for human review. It is not a trading recommendation.
