# ServLoci Colab Notebook Series

A twenty-four-part Google Colab series covering the [ServLoci](https://comm.servloci.in)
Python SDK, options-pricing math, strategy construction, a full algo-trading
workflow, 18 documented Indian broker APIs, 50 technical indicators and alert
delivery — plus a standalone, current DhanHQ quickstart.

Every notebook is self-contained: open it in Colab, run top to bottom. Broker
and live-data notebooks fall back to a safe **demo mode** when no credentials
are set, so the whole series runs cleanly with zero setup.

## Where to run the workload

Use Colab for interactive analytics, indicators and backtests, then use
ServLoci as the stable broker-facing exit for approved order calls. A small
1 GB or shared-CPU VPS can run out of memory or become unresponsive under
heavy pandas, Jupyter, backtesting or multi-feed workloads; free and low-cost
providers may also apply burst or fair-use limits.

StaticIP is the network lane, not another compute server. Install
\`trading-static-ip\`, call \`configure()\` before constructing the broker SDK,
and keep unrelated notebook traffic direct. Colab runtimes can disconnect and
their limits vary, so move unattended 24x7 strategies to persistent managed
compute while keeping the same ServLoci exit route.

## Get your static IP

Each notebook's setup cell explains this, but in short:

1. Sign up free at [comm.servloci.in/register](https://comm.servloci.in/register)
   (or [comm.servloci.in/auth/google?free=1](https://comm.servloci.in/auth/google?free=1)
   for an instant Google-login trial).
2. Your `api_key` / `api_secret` pair appears in your portal at
   [comm.servloci.in/user](https://comm.servloci.in/user).
3. Set them as Colab secrets or environment variables (`SERVLOCI_API_KEY`,
   `SERVLOCI_API_SECRET`) before running — or leave them unset to explore in
   demo mode.

Full docs: [comm.servloci.in/docs](https://comm.servloci.in/docs). SDK source
served live at [comm.servloci.in/sdk/servloci.py](https://comm.servloci.in/sdk/servloci.py).
Rendered (read-only) output for every notebook is served statically at
[comm.servloci.in/notebooks/](https://comm.servloci.in/notebooks/) — no Colab
account needed just to read them.

## Complete Dhan Colab quickstart

Use [colab_dhan_trading_static_ip.ipynb](colab_dhan_trading_static_ip.ipynb)
for the current one-token flow with `trading-static-ip==0.3.1` and DhanHQ 2.2.
It clears stale 0.3.0 proxy state before installation, reads credentials from
Colab Secrets, verifies the assigned IPv6, initializes the current
`DhanContext` API, and performs a read-only account call before showing a
dry-run order payload.

## Notebooks

| # | Notebook | What it covers |
|---|----------|-----------------|
| 00 | [Get Your Static IP & Verify It](00_get_static_ip_and_verify.ipynb) | Claim a dedicated static IPv6 and confirm your egress IP actually changes. |
| 01 | [ServLoci SDK Quickstart](01_servloci_sdk_quickstart.ipynb) | The four ways to use the `ServLoci` Python class. |
| 02 | [Broker Auth: Zerodha (Kite Connect)](02_broker_auth_zerodha_kite.ipynb) | Authenticate and place a demo order via Kite Connect over your static IP. |
| 03 | [Broker Auth: Dhan](03_broker_auth_dhan.ipynb) | Authenticate and place a demo order via DhanHQ v2 over your static IP. |
| 04 | [Broker Auth: Groww](04_broker_auth_groww.ipynb) | Authenticate and place a demo order via the Groww Trade API over your static IP. |
| 05 | [Broker Auth: Fyers](05_broker_auth_fyers.ipynb) | Authenticate and place a demo order via the FYERS API over your static IP. |
| 06 | [Black-Scholes Pricing & Greeks](06_black_scholes_pricing_greeks.ipynb) | Option price, delta, gamma, theta, vega — ported from the site's pricer. |
| 07 | [Option Payoff & Breakeven Calculator](07_option_payoff_breakeven_calculator.ipynb) | Multi-leg payoff curves, breakevens, and max profit/loss at expiry. |
| 08 | [Strategy: Straddle & Strangle](08_strategy_straddle_strangle.ipynb) | Long straddle, short straddle, and long strangle templates with payoff charts. |
| 09 | [Strategy: Vertical Spreads](09_strategy_vertical_spreads.ipynb) | Bull call spread and bear call spread templates with payoff charts. |
| 10 | [Strategy: Iron Condor](10_strategy_iron_condor.ipynb) | Four-leg range-bound strategy template with a payoff chart. |
| 11 | [Live Option Chain Fetch](11_live_option_chain_fetch.ipynb) | Pull live NIFTY/BANKNIFTY strikes from ServLoci's public option-chain endpoint. |
| 12 | [Implied Volatility Skew](12_implied_volatility_surface.ipynb) | Back out per-strike IV from live premiums via bisection. |
| 13 | [Historical Data for Backtesting](13_historical_data_for_backtesting.ipynb) | Pull 2 years of NIFTY daily closes for the backtests that follow. |
| 14 | [Backtest: Weekly Short Straddle](14_backtest_options_strategy.ipynb) | A simplified, cost-free backtest of a weekly ATM short straddle. |
| 15 | [Position Sizing & Risk Management](15_position_sizing_risk_management.ipynb) | Fixed-fractional lot sizing and a hard max-loss guardrail. |
| 16 | [Order Management System](16_order_management_system.ipynb) | Place, modify, and cancel orders through a ServLoci-proxied session. |
| 17 | [Paper Trading Loop](17_paper_trading_loop.ipynb) | An SMA-crossover signal tracked as simulated paper trades. |
| 18 | [Signal-to-Order Pipeline](18_signal_to_order_pipeline.ipynb) | Poll a signal source and dry-run dispatch to an OMS. |
| 19 | [Capstone: End-to-End Algo Bot](19_capstone_end_to_end_algo_bot.ipynb) | SDK + strategy template + risk sizing + dry-run OMS dispatch, combined. |
| 20 | [Indian Broker API Landscape](20_indian_broker_api_landscape.ipynb) | 18 public, first-party Indian broker API sources, capabilities, auth and ServLoci support status. |
| 21 | [Top 50 Technical Indicators](21_top_50_technical_indicators.ipynb) | Dependency-light implementations of 50 trend, momentum, volatility, directional and volume indicators. |
| 22 | [Broker Data to Indicator Pipeline](22_broker_data_indicator_pipeline.ipynb) | Normalize broker candles once and compute the full indicator set. |
| 23 | [Alerts and ServLoci Dispatch](23_alerts_and_servloci_dispatch.ipynb) | De-duplicated console/webhook/Telegram alerts with a dry-run order boundary. |

## Indicator learning path

Start at notebook 20 to compare broker surfaces, compute and inspect the 50
indicators in notebook 21, plug broker candles into the normalized pipeline in
notebook 22, then add stateful alerts and a risk-gated ServLoci dispatch boundary
in notebook 23. Market-data reads remain direct; only approved broker order calls
need the stable ServLoci egress.

## Try it live

The options-math notebooks (06-10) are a runnable companion to the free
[Strategy Builder](https://comm.servloci.in/tools/strategy-builder) tool —
same payoff/breakeven math, same strategy templates.

## Source repo

This series lives at
[github.com/ivikasavnish/algo-trading-notebooks](https://github.com/ivikasavnish/algo-trading-notebooks)
(kept separate from the main app repo so the collection can grow
without dragging app code along). Each notebook's "Open in Colab" badge
points there. `generate_notebooks.py`'s `GITHUB_REPO` constant controls the
badge target — update it and rerun the generator if the notebooks ever move
to a different repo.
