# ATOS Manual Validation Matrix

Purpose: use this repository as the external manual/reference validation layer for ATOS in trading-agent-python. These notebooks are not production dependencies. A notebook passing does not by itself prove ATOS correctness.

Validation flow: Notebook -> reference/observed behaviour -> ATOS component -> manual comparison -> automated regression candidate.

Status: PLANNED, MANUAL-PASS, MANUAL-FAIL, BLOCKED, AUTOMATED.

## M2 Market Data

| ID | Notebook | ATOS component | Manual validation | Expected invariant |
|---|---|---|---|---|
| MD-001 | 13 Historical Data | Provider/ingestion/dataset | Compare timestamps, rows and OHLC on same instrument/range | No unexplained missing, duplicate or out-of-order observations |
| MD-002 | 21 Technical Indicators | Canonical bars/features | Run indicators on canonical OHLCV | Same inputs produce deterministic features |
| MD-003 | 22 Broker Data -> Indicators | Provider/canonical model | Compare provider candles with canonical candles | Provider-specific fields do not alter canonical OHLC semantics |
| MD-004 | 24 Reading Market with yfinance | Price policy/corporate actions | Compare Close vs Adj Close | RAW/ADJUSTED/UNKNOWN is explicit; no silent adjustment |
| MD-005 | 25 Returns/Volatility/Risk | Dataset/features | Recompute metrics from fixed dataset | Same dataset/version produces reproducible metrics |
| MD-006 | 27 Indicators Tested Honestly | Research/temporal semantics | Compare indicator and forward-return alignment | No future observations enter historical features |
| MD-007 | 32 Correlation/Pairs | Dataset/features | Recompute correlation from fixed dataset | Same aligned observations produce same matrix |

## Derivatives

| ID | Notebook | ATOS component | Manual validation | Expected invariant |
|---|---|---|---|---|
| DER-001 | 06 Black-Scholes/Greeks | Quant reference | Compare price and Greeks for identical inputs | Deterministic inputs produce deterministic outputs |
| DER-002 | 07 Payoff/Breakeven | Strategy math | Compare multi-leg payoff and breakevens | Leg signs, strikes and premiums are preserved |
| DER-003 | 08 Straddle/Strangle | Strategy model | Compare strategy legs/payoff | Composition is deterministic |
| DER-004 | 09 Vertical Spreads | Strategy model | Compare spread construction/payoff | Long/short legs and strike ordering are correct |
| DER-005 | 10 Iron Condor | Strategy model | Compare four-leg construction/payoff | All four legs retain correct identity |
| DER-006 | 11 Live Option Chain | Option-chain model | Compare underlying, expiry, strike, type, LTP/OI/Greeks | Instrument identity is explicit |
| DER-007 | 12 IV Surface | Option-chain/quant | Compare IV by strike/expiry | IV maps to correct option identity |
| DER-008 | 28 Options Priced Against Reality | Pricing/data | Compare theoretical and observed inputs | Model price is not treated as executable market price |

## Research and backtesting

| ID | Notebook | ATOS component | Manual validation | Expected invariant |
|---|---|---|---|---|
| RES-001 | 14 Options Strategy Backtest | Backtest | Re-run documented strategy on fixed dataset | Same dataset and parameters reproduce trades/results |
| RES-002 | 27 Technical Indicators Tested Honestly | Research validation | Verify indicator/forward-return alignment | No lookahead leakage |
| RES-003 | 29 Backtesting Without Fooling Yourself | Research validation | Compare biased and correctly aligned workflows | Future information never enters historical decisions |
| RES-004 | 31 Capstone | Research lifecycle | Run end-to-end workflow | Inputs, parameters and outputs are traceable |
| RES-005 | 33 Return Prediction Baselines | Model evaluation | Compare model with naive baseline on OOS data | Baseline is explicit and evaluated on same OOS period |

## Risk and portfolio

| ID | Notebook | ATOS component | Manual validation | Expected invariant |
|---|---|---|---|---|
| RISK-001 | 15 Position Sizing | Risk engine | Verify size from capital/risk/stop assumptions | Hard max-loss constraint cannot be bypassed |
| RISK-002 | 25 Returns/Volatility/Risk | Risk metrics | Recompute volatility, Sharpe, Sortino, drawdown | Definitions are explicit and reproducible |
| RISK-003 | 30 Position Sizing/Risk of Ruin | Risk engine | Compare Monte Carlo assumptions/results | Simulation inputs are explicit |
| RISK-004 | 32 Correlation/Pairs | Correlation engine | Compare rolling correlation | Window/alignment semantics are explicit |
| RISK-005 | 34 Portfolio Analytics | Portfolio engine | Compare weights, covariance, return/volatility/drawdown | Metrics derive from exact dataset/version |

## Execution and OMS

| ID | Notebook | ATOS component | Manual validation | Expected invariant |
|---|---|---|---|---|
| EXE-001 | 16 OMS | OMS boundary | Exercise create/modify/cancel in dry-run | Lifecycle transitions are valid and deterministic |
| EXE-002 | 17 Paper Trading | Paper execution | Run signal -> simulated position lifecycle | No real order is placed; state is reproducible |
| EXE-003 | 18 Signal -> Order | Decision/OMS boundary | Feed known signal and inspect order | Signal and order remain separately traceable |
| EXE-004 | 19 End-to-End Algo Bot | Architecture | Execute capstone in dry-run | Strategy, sizing, risk and OMS boundaries remain distinct |
| EXE-005 | 23 Alerts/Dispatch | Alert boundary | Trigger duplicate/repeated signals | Deduplication prevents duplicate dispatch |

## Provider validation

| ID | Notebook | ATOS component | Manual validation | Expected invariant |
|---|---|---|---|---|
| PROV-001 | 02 Zerodha Auth | Provider boundary | Validate auth/demo behaviour | Credentials stay outside canonical domain models |
| PROV-002 | 03 Dhan Auth | Provider boundary | Validate auth/demo behaviour | Provider auth remains outside domain contracts |
| PROV-003 | 04 Groww Auth | Provider boundary | Validate auth/demo behaviour | Canonical boundary is provider-independent |
| PROV-004 | 05 FYERS Auth | FYERS adapter | Validate FYERS behaviour | FYERS payloads normalize to canonical contracts |
| PROV-005 | 20 Broker API Landscape | Capability model | Compare documented capabilities with ATOS | Capabilities are verified, not assumed |

## Priority

Wave 1: MD-001, MD-003, MD-004, MD-005, MD-006, DER-006, DER-007.

Wave 2: RES-001, RES-002, RES-003, RES-005, RISK-002, RISK-004.

Wave 3: RISK-001, RISK-003, RISK-005.

Wave 4: EXE-001 through EXE-005.

## Evidence record

Record: Test ID; notebook commit; ATOS commit; provider; instrument; asset class; date range; interval; timezone; dataset ID/version; price policy; parameters; expected; observed; result; evidence; defect; automated regression candidate.

For market-data tests also record provider symbol, canonical instrument_id, provider timestamp, observation timestamp, ingestion timestamp, raw_record_id, canonical_record_id, dataset hash and quality events.

## Failure classification

Classify failures before changing ATOS: DATA_SOURCE, CANONICALIZATION, QUALITY, RESEARCH, RISK, or EXECUTION.

Examples: provider discrepancy, stale/missing data, instrument identity, timestamp, OHLC, duplicate, out-of-order, missing interval, outside session, leakage, wrong alignment, non-reproducibility, sizing, exposure, drawdown, portfolio aggregation, signal, order construction, lifecycle or duplicate dispatch.

## Boundary

This repository remains separate from the ATOS runtime. It is an external consumer/reference implementation. Stable manual findings should be promoted into automated regression or contract tests in trading-agent-python.

M2 external validation is complete when canonical OHLC behaviour has been checked against an independent consumer; raw/adjusted semantics are reconciled; data-quality and derivative-identity behaviour has been exercised; dataset reproducibility and temporal-leakage checks have been exercised; and stable findings have automated regression candidates.