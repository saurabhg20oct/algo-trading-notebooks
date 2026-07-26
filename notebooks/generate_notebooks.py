#!/usr/bin/env python3
"""Generates notebooks/*.ipynb — the ServLoci algo/options trading series.

Run: python notebooks/generate_notebooks.py
Regenerates all 20 .ipynb files in this directory from the templates below.
"""
import json
import os

# Swap once the repo is pushed to a real GitHub location — badges resolve
# against github.com/<GITHUB_REPO>/blob/<BRANCH>/notebooks/<file>.
GITHUB_REPO = "ivikasavnish/algo-trading-notebooks"
BRANCH = "main"
SITE = "https://comm.servloci.in"

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def _lines(text):
    text = text.strip("\n")
    if not text:
        return []
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + [parts[-1]]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _lines(text),
    }


def colab_badge(filename):
    url = f"https://colab.research.google.com/github/{GITHUB_REPO}/blob/{BRANCH}/notebooks/{filename}"
    return f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})"


def header_cells(idx, filename, title, subtitle):
    text = f"""# {title}

{colab_badge(filename)}

{subtitle}

Part {idx:02d} of 20 in the [ServLoci algo/options trading notebook series]({SITE}/docs) — full index in `notebooks/README.md`.
"""
    return [md(text)]


def setup_cells():
    text = """# Get your dedicated static IPv6 + SOCKS5 credentials free:
#   https://comm.servloci.in/register        (or /auth/google?free=1 for an instant trial)
# Your api_key / api_secret pair shows up in the portal after signup:
#   https://comm.servloci.in/user
!pip install -q "requests[socks]"
!curl -sL https://comm.servloci.in/sdk/servloci.py -o servloci.py

import os
from servloci import ServLoci

SERVLOCI_API_KEY = os.environ.get("SERVLOCI_API_KEY", "dhan:1000000001")   # broker:client_id
SERVLOCI_API_SECRET = os.environ.get("SERVLOCI_API_SECRET", "")            # from the portal — leave blank to run this notebook in demo mode

sl = None
if SERVLOCI_API_SECRET:
    sl = ServLoci(api_key=SERVLOCI_API_KEY, api_secret=SERVLOCI_API_SECRET)
    print("ServLoci configured:", sl.host, sl.port)
else:
    print("SERVLOCI_API_SECRET not set — running in demo mode (no live proxy calls).")
"""
    return [md("## Setup"), code(text)]


def footer_cells(idx):
    nav = []
    if idx > 0:
        p = NOTEBOOKS[idx - 1]
        nav.append(f"« Previous: [{p['title']}]({p['filename']})")
    if idx < len(NOTEBOOKS) - 1:
        n = NOTEBOOKS[idx + 1]
        nav.append(f"Next: [{n['title']}]({n['filename']}) »")
    nav_line = "  \n".join(nav)
    text = f"""---

{nav_line}

Try the concepts above interactively: [Options Strategy Builder]({SITE}/tools/strategy-builder) · [Docs]({SITE}/docs) · [Get your static IP]({SITE}/register)
"""
    return [md(text)]


# ── Reusable code blocks ported from shared/lib + shared/data ──────────────

BS_PRICE_SRC = """from scipy.stats import norm
import math

def bs_price(opt_type, spot, strike, t_years, vol, rate=0.065):
    if t_years <= 0 or vol <= 0:
        return max(spot - strike, 0) if opt_type == "CE" else max(strike - spot, 0)
    d1 = (math.log(spot / strike) + (rate + vol * vol / 2) * t_years) / (vol * math.sqrt(t_years))
    d2 = d1 - vol * math.sqrt(t_years)
    if opt_type == "CE":
        return spot * norm.cdf(d1) - strike * math.exp(-rate * t_years) * norm.cdf(d2)
    return strike * math.exp(-rate * t_years) * norm.cdf(-d2) - spot * norm.cdf(-d1)
"""

STRATEGY_MATH_SRC = """def leg_payoff_at_expiry(leg, underlying_price):
    iv = max(underlying_price - leg["strike"], 0) if leg["type"] == "CE" else max(leg["strike"] - underlying_price, 0)
    sign = 1 if leg["side"] == "buy" else -1
    return sign * (iv - leg["premium"]) * leg["qty"]

def strategy_payoff_at_expiry(legs, underlying_price):
    return sum(leg_payoff_at_expiry(leg, underlying_price) for leg in legs)

def net_premium(legs):
    return sum((-1 if leg["side"] == "buy" else 1) * leg["premium"] * leg["qty"] for leg in legs)

def payoff_curve(legs, spot, rng=0.15, steps=120):
    lo, hi = spot * (1 - rng), spot * (1 + rng)
    pts = []
    for i in range(steps + 1):
        p = lo + (hi - lo) * i / steps
        pts.append({"price": p, "pnl": strategy_payoff_at_expiry(legs, p)})
    return pts

def breakevens(points):
    crossings = []
    for a, b in zip(points, points[1:]):
        if (a["pnl"] < 0 <= b["pnl"]) or (a["pnl"] > 0 >= b["pnl"]):
            t = 0 if a["pnl"] == b["pnl"] else -a["pnl"] / (b["pnl"] - a["pnl"])
            crossings.append(a["price"] + t * (b["price"] - a["price"]))
    return crossings

def max_profit_loss(points):
    pnls = [p["pnl"] for p in points]
    return {"maxProfit": max(pnls), "maxLoss": min(pnls)}
"""

TEMPLATE_HELPERS_SRC = """def nearest_strike(spot, step):
    return round(spot / step) * step

def find_premium(chain, strike, opt_type):
    if not chain:
        return 0
    row = next((r for r in chain if r["strike"] == strike), None)
    if not row:
        return 0
    leg = row.get("ce" if opt_type == "CE" else "pe")
    return leg["ltp"] if leg and isinstance(leg.get("ltp"), (int, float)) else 0

def fill_demo_premiums(legs, spot, t_years=7 / 365, vol=0.13):
    for leg in legs:
        if not leg["premium"]:
            leg["premium"] = round(bs_price(leg["type"], spot, leg["strike"], t_years, vol), 2)
    return legs
"""

PLOT_HELPER_SRC = """import matplotlib.pyplot as plt

def plot_payoff(points, title):
    xs = [p["price"] for p in points]
    ys = [p["pnl"] for p in points]
    plt.axhline(0, color="grey", linewidth=0.8)
    plt.plot(xs, ys)
    plt.title(title)
    plt.xlabel("Underlying spot")
    plt.ylabel("P&L (INR)")
    plt.show()
"""


# ── Per-notebook bodies ──────────────────────────────────────────────────

def body_00_get_static_ip():
    return [
        md("Claim a dedicated static IPv6, then verify your egress IP actually changes when you route through it — this is the IP you'll whitelist with your broker."),
        code("""import requests

direct_ip = requests.get("https://api.ipify.org?format=json", timeout=8).json()["ip"]
print("Direct egress IP (Colab's own — NOT yours):", direct_ip)

if sl:
    proxied_ip = sl.session().get("https://api.ipify.org?format=json", timeout=8).json()["ip"]
    print("Proxied egress IP (whitelist THIS with your broker):", proxied_ip)
    assert proxied_ip != direct_ip, "expected the proxy to change the egress IP"
else:
    print("Set SERVLOCI_API_SECRET above (get it free at https://comm.servloci.in/register), then re-run this cell.")
"""),
        md("Next: whitelist the printed IPv6 in your broker's API console (see notebooks 02-05 for the per-broker steps), then move on to the SDK quickstart."),
    ]


def body_01_sdk_quickstart():
    return [
        md("The SDK has four surfaces: `proxy_url()` / `proxies()` for raw URLs, `export_env()` for env-based tools, `session()` for a scoped `requests.Session`, and `attach()` to monkey-patch every future `requests.Session` process-wide."),
        code("""from servloci import ServLoci, configure

demo = ServLoci(api_key="dhan:1000000001", api_secret="demo-secret")
print("proxy_url():", demo.proxy_url())
print("proxies():  ", demo.proxies())

try:
    ServLoci(api_key="", api_secret="")
except ValueError as e:
    print("Missing credentials raise ValueError:", e)

if sl:
    sl.export_env()
    print("HTTPS_PROXY set in os.environ:", "HTTPS_PROXY" in os.environ)
    s = sl.session()
    print("session() proxies:", s.proxies)
"""),
        md("`attach()` must run **before** you import a broker SDK — dhanhq, kiteconnect, growwapi and fyers-apiv3 all create a `requests.Session` at import time. The one-liner `servloci.configure(api_key, api_secret)` does `ServLoci(...).attach()` in a single call."),
    ]


def _broker_body(name, pip_pkg, support_note, snippet):
    return [
        md(f"**Support level:** {support_note}"),
        code(f"""if sl:
    sl.attach()  # BEFORE importing {pip_pkg} — it creates a requests.Session at import time
{snippet}
else:
    print("Demo mode — set SERVLOCI_API_SECRET above to run this against your {name} account.")
"""),
        md(f"Install the broker SDK separately: `!pip install -q {pip_pkg}`. Full whitelist steps: [{SITE}/docs/brokers]({SITE}/docs)."),
    ]


def body_02_zerodha():
    return _broker_body(
        "Zerodha",
        "kiteconnect",
        "Self-service — Kite Connect apps are approved instantly from the developer console; add your ServLoci IPv6 there.",
        """    from kiteconnect import KiteConnect

    kite = KiteConnect(api_key=os.environ.get("KITE_API_KEY", ""))
    print("Login URL:", kite.login_url())
    # After the browser redirect, exchange request_token for an access_token:
    # data = kite.generate_session(request_token, api_secret=os.environ["KITE_API_SECRET"])
    # kite.set_access_token(data["access_token"])
    # order_id = kite.place_order(tradingsymbol="INFY", exchange=kite.EXCHANGE_NSE,
    #                              transaction_type=kite.TRANSACTION_TYPE_BUY, quantity=1,
    #                              order_type=kite.ORDER_TYPE_MARKET, product=kite.PRODUCT_MIS,
    #                              variety=kite.VARIETY_REGULAR)""",
    )


def body_03_dhan():
    return _broker_body(
        "Dhan",
        "dhanhq",
        "Assisted review — DhanHQ v2 API access is granted via a support ticket; mention your ServLoci IPv6 in the request.",
        """    from dhanhq import dhanhq

    dhan = dhanhq(client_id=os.environ.get("DHAN_CLIENT_ID", ""), access_token=os.environ.get("DHAN_ACCESS_TOKEN", ""))
    print("Dhan client ready:", dhan.client_id)
    # order = dhan.place_order(security_id="1333", exchange_segment=dhan.NSE, transaction_type=dhan.BUY,
    #                           quantity=1, order_type=dhan.MARKET, product_type=dhan.INTRA, price=0)""",
    )


def body_04_groww():
    return _broker_body(
        "Groww",
        "growwapi",
        "Support-confirmed workflow — Groww enables Trade API access per-account after a confirmation email; include your ServLoci IP in that thread.",
        """    from growwapi import GrowwAPI

    groww = GrowwAPI(os.environ.get("GROWW_ACCESS_TOKEN", ""))
    print("Groww client ready")
    # order = groww.place_order(trading_symbol="INFY", quantity=1, order_type="MARKET",
    #                            transaction_type="BUY", segment="CASH", product="MIS")""",
    )


def body_05_fyers():
    return _broker_body(
        "Fyers",
        "fyers-apiv3",
        "Confirmation flow for individual and family accounts — FYERS support verifies the requesting IP before enabling API trading.",
        """    from fyers_apiv3 import fyersModel

    fyers = fyersModel.FyersModel(client_id=os.environ.get("FYERS_CLIENT_ID", ""),
                                   token=os.environ.get("FYERS_ACCESS_TOKEN", ""), is_async=False)
    print("Fyers client ready")
    # order = fyers.place_order(data={"symbol": "NSE:INFY-EQ", "qty": 1, "type": 2,
    #                                  "side": 1, "productType": "INTRADAY"})""",
    )


def body_06_black_scholes():
    return [
        md("Python port of `shared/lib/blackScholes.js` — the exact pricer behind `/tools/strategy-builder`, swapping the hand-rolled `erf` approximation for `scipy.stats.norm`."),
        code(BS_PRICE_SRC + """
def greeks(opt_type, spot, strike, t_years, vol, rate=0.065):
    if t_years <= 0 or vol <= 0:
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
    d1 = (math.log(spot / strike) + (rate + vol * vol / 2) * t_years) / (vol * math.sqrt(t_years))
    d2 = d1 - vol * math.sqrt(t_years)
    nd1 = norm.pdf(d1)
    delta = norm.cdf(d1) if opt_type == "CE" else norm.cdf(d1) - 1
    gamma = nd1 / (spot * vol * math.sqrt(t_years))
    vega = (spot * nd1 * math.sqrt(t_years)) / 100  # per 1% vol move
    term1 = -(spot * nd1 * vol) / (2 * math.sqrt(t_years))
    if opt_type == "CE":
        theta = (term1 - rate * strike * math.exp(-rate * t_years) * norm.cdf(d2)) / 365
    else:
        theta = (term1 + rate * strike * math.exp(-rate * t_years) * norm.cdf(-d2)) / 365
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}

spot, strike, t_years, vol = 24000, 24000, 7 / 365, 0.13
print("CE price:", round(bs_price("CE", spot, strike, t_years, vol), 2))
print("CE greeks:", {k: round(v, 4) for k, v in greeks("CE", spot, strike, t_years, vol).items()})
"""),
    ]


def body_07_payoff_breakeven():
    return [
        md("Python port of `shared/lib/strategyMath.js` — payoff is computed **at expiry** (intrinsic value only), same as the payoff chart on `/tools/strategy-builder`."),
        code(STRATEGY_MATH_SRC + """
legs = [
    {"side": "buy", "type": "CE", "strike": 24000, "premium": 180, "qty": 75},
    {"side": "sell", "type": "CE", "strike": 24200, "premium": 90, "qty": 75},
]
points = payoff_curve(legs, spot=24000)
print("Net premium:", net_premium(legs))
print("Breakevens:", breakevens(points))
print("Max P/L:", max_profit_loss(points))
"""),
        code(PLOT_HELPER_SRC + '\nplot_payoff(points, "Bull call spread payoff at expiry")'),
    ]


def body_08_straddle_strangle():
    return [
        md("Port of the `long_straddle` / `short_straddle` / `long_strangle` templates from `shared/data/strategyTemplates.js`. Premiums are backfilled with Black-Scholes (notebook 06) since no live chain is passed in demo mode — swap in a real chain from notebook 11 for live premiums."),
        code(BS_PRICE_SRC + STRATEGY_MATH_SRC + TEMPLATE_HELPERS_SRC + """
def long_straddle(spot, step, chain=None, qty=1):
    atm = nearest_strike(spot, step)
    return [
        {"side": "buy", "type": "CE", "strike": atm, "premium": find_premium(chain, atm, "CE"), "qty": qty},
        {"side": "buy", "type": "PE", "strike": atm, "premium": find_premium(chain, atm, "PE"), "qty": qty},
    ]

def short_straddle(spot, step, chain=None, qty=1):
    atm = nearest_strike(spot, step)
    return [
        {"side": "sell", "type": "CE", "strike": atm, "premium": find_premium(chain, atm, "CE"), "qty": qty},
        {"side": "sell", "type": "PE", "strike": atm, "premium": find_premium(chain, atm, "PE"), "qty": qty},
    ]

def long_strangle(spot, step, chain=None, qty=1):
    atm = nearest_strike(spot, step)
    call_strike, put_strike = atm + 2 * step, atm - 2 * step
    return [
        {"side": "buy", "type": "CE", "strike": call_strike, "premium": find_premium(chain, call_strike, "CE"), "qty": qty},
        {"side": "buy", "type": "PE", "strike": put_strike, "premium": find_premium(chain, put_strike, "PE"), "qty": qty},
    ]

SPOT, STEP = 24000, 50
"""),
        code(PLOT_HELPER_SRC + """
for name, builder in [("Long straddle", long_straddle), ("Short straddle", short_straddle), ("Long strangle", long_strangle)]:
    legs = fill_demo_premiums(builder(SPOT, STEP), SPOT)
    points = payoff_curve(legs, SPOT)
    print(name, "max P/L:", max_profit_loss(points))
    plot_payoff(points, name)
"""),
    ]


def body_09_vertical_spreads():
    return [
        md("Port of `bull_call_spread` / `bear_call_spread` from `shared/data/strategyTemplates.js` — capped-risk directional strategies."),
        code(BS_PRICE_SRC + STRATEGY_MATH_SRC + TEMPLATE_HELPERS_SRC + """
def bull_call_spread(spot, step, chain=None, qty=1):
    atm = nearest_strike(spot, step)
    higher = atm + 2 * step
    return [
        {"side": "buy", "type": "CE", "strike": atm, "premium": find_premium(chain, atm, "CE"), "qty": qty},
        {"side": "sell", "type": "CE", "strike": higher, "premium": find_premium(chain, higher, "CE"), "qty": qty},
    ]

def bear_call_spread(spot, step, chain=None, qty=1):
    atm = nearest_strike(spot, step)
    higher = atm + 2 * step
    return [
        {"side": "sell", "type": "CE", "strike": atm, "premium": find_premium(chain, atm, "CE"), "qty": qty},
        {"side": "buy", "type": "CE", "strike": higher, "premium": find_premium(chain, higher, "CE"), "qty": qty},
    ]

SPOT, STEP = 24000, 50
"""),
        code(PLOT_HELPER_SRC + """
for name, builder in [("Bull call spread", bull_call_spread), ("Bear call spread", bear_call_spread)]:
    legs = fill_demo_premiums(builder(SPOT, STEP), SPOT)
    points = payoff_curve(legs, SPOT)
    print(name, "max P/L:", max_profit_loss(points))
    plot_payoff(points, name)
"""),
    ]


def body_10_iron_condor():
    return [
        md("Port of `iron_condor` from `shared/data/strategyTemplates.js` — sell the near wings, buy the far wings, profit if price stays range-bound."),
        code(BS_PRICE_SRC + STRATEGY_MATH_SRC + TEMPLATE_HELPERS_SRC + """
def iron_condor(spot, step, chain=None, qty=1):
    atm = nearest_strike(spot, step)
    sell_call, buy_call = atm + 2 * step, atm + 4 * step
    sell_put, buy_put = atm - 2 * step, atm - 4 * step
    return [
        {"side": "sell", "type": "CE", "strike": sell_call, "premium": find_premium(chain, sell_call, "CE"), "qty": qty},
        {"side": "buy", "type": "CE", "strike": buy_call, "premium": find_premium(chain, buy_call, "CE"), "qty": qty},
        {"side": "sell", "type": "PE", "strike": sell_put, "premium": find_premium(chain, sell_put, "PE"), "qty": qty},
        {"side": "buy", "type": "PE", "strike": buy_put, "premium": find_premium(chain, buy_put, "PE"), "qty": qty},
    ]

SPOT, STEP = 24000, 50
legs = fill_demo_premiums(iron_condor(SPOT, STEP), SPOT)
points = payoff_curve(legs, SPOT)
print("Net premium:", net_premium(legs))
print("Breakevens:", breakevens(points))
print("Max P/L:", max_profit_loss(points))
"""),
        code(PLOT_HELPER_SRC + '\nplot_payoff(points, "Iron condor payoff at expiry")'),
    ]


def body_11_live_chain():
    return [
        md("No proxy needed for this one — this hits ServLoci's own public option-chain endpoint (5s server-side cache), the same one `/tools/strategy-builder` uses."),
        code("""import requests

resp = requests.get("https://comm.servloci.in/api/market/option-chain", params={"symbol": "NIFTY"}, timeout=10)
resp.raise_for_status()
data = resp.json()
spot, chain = data.get("spot"), data.get("strikes", [])
print("Spot:", spot, "| strikes returned:", len(chain))
chain[:5]
"""),
        md("`chain` is shaped `[{strike, ce: {ltp, ...}, pe: {ltp, ...}}, ...]` — pass it straight into the `find_premium()` / template builders from notebooks 08-10 for real (not Black-Scholes-estimated) premiums."),
    ]


def body_12_iv_surface():
    return [
        md("Backs out implied volatility per strike via bisection against the Black-Scholes pricer (notebook 06), using live chain LTPs (notebook 11) — a rough call-side skew, not a full surface (single expiry assumption below)."),
        code(BS_PRICE_SRC + """
def implied_vol(opt_type, spot, strike, t_years, market_price, rate=0.065, lo=0.01, hi=3.0, iters=60):
    for _ in range(iters):
        mid = (lo + hi) / 2
        if bs_price(opt_type, spot, strike, t_years, mid, rate) > market_price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2

import requests

resp = requests.get("https://comm.servloci.in/api/market/option-chain", params={"symbol": "NIFTY"}, timeout=10)
data = resp.json()
spot, chain = data.get("spot", 24000), data.get("strikes", [])

t_years = 7 / 365  # placeholder — replace with actual days-to-expiry / 365
strikes, ivs = [], []
for row in chain:
    ltp = (row.get("ce") or {}).get("ltp")
    if isinstance(ltp, (int, float)) and ltp > 0:
        strikes.append(row["strike"])
        ivs.append(implied_vol("CE", spot, row["strike"], t_years, ltp) * 100)
"""),
        code("""import matplotlib.pyplot as plt

plt.plot(strikes, ivs, marker="o")
plt.axvline(spot, color="grey", linestyle="--", label="spot")
plt.title("NIFTY call IV skew (single-expiry proxy)")
plt.xlabel("Strike")
plt.ylabel("Implied vol (%)")
plt.legend()
plt.show()
"""),
    ]


def body_13_historical_data():
    return [
        md("Pulls historical NIFTY closes for the backtesting notebooks that follow. No ServLoci proxy needed — Yahoo Finance is publicly reachable."),
        code("""!pip install -q yfinance
import yfinance as yf

nifty = yf.download("^NSEI", period="2y", interval="1d", progress=False)
nifty.to_csv("nifty_2y.csv")
print(nifty.tail())
"""),
        md("`nifty_2y.csv` is reused by notebooks 14 and 17 — re-run this cell first if you're opening those standalone."),
    ]


def body_14_backtest():
    return [
        md("**Illustrative only** — no slippage, costs, or margin. Sells a weekly ATM straddle every Monday, priced with 20-day realized vol via Black-Scholes (notebook 06), held to Friday's close."),
        code(BS_PRICE_SRC + """
import pandas as pd
import math

nifty = pd.read_csv("nifty_2y.csv", index_col=0, parse_dates=True)
nifty["ret"] = nifty["Close"].pct_change()
nifty["realized_vol"] = nifty["ret"].rolling(20).std() * math.sqrt(252)

trades = []
mondays = nifty[nifty.index.weekday == 0].dropna(subset=["realized_vol"])
for entry_date, row in mondays.iterrows():
    exit_idx = nifty.index.searchsorted(entry_date) + 4  # ~Friday, 5 trading days later
    if exit_idx >= len(nifty):
        continue
    spot_in, spot_out = row["Close"], nifty["Close"].iloc[exit_idx]
    vol, t_years = row["realized_vol"], 5 / 252
    strike = round(spot_in / 50) * 50
    call_prem = bs_price("CE", spot_in, strike, t_years, vol)
    put_prem = bs_price("PE", spot_in, strike, t_years, vol)
    payoff = -(max(spot_out - strike, 0) - call_prem) - (max(strike - spot_out, 0) - put_prem)
    trades.append({"entry": entry_date, "spot_in": spot_in, "spot_out": spot_out, "pnl_per_lot": payoff})

results = pd.DataFrame(trades)
print(results.tail())
print("Total simulated P&L (1 lot, no costs):", round(results["pnl_per_lot"].sum(), 2))
"""),
    ]


def body_15_position_sizing():
    return [
        md("Fixed-fractional sizing + a hard max-loss guardrail — feed `max_loss_per_lot` from notebook 07/10's `max_profit_loss()` output for a real strategy."),
        code("""def position_size(capital, risk_pct, max_loss_per_lot):
    \"\"\"How many lots keep max loss within risk_pct of capital.\"\"\"
    if max_loss_per_lot <= 0:
        return 0
    return max(int((capital * risk_pct) // max_loss_per_lot), 0)

capital = 500_000
risk_pct = 0.02  # risk 2% of capital per trade
max_loss_per_lot = 4500  # from max_profit_loss()["maxLoss"] for one lot, notebooks 07/10

lots = position_size(capital, risk_pct, abs(max_loss_per_lot))
print(f"Capital Rs.{capital:,} at {risk_pct:.0%} risk -> {lots} lot(s), max loss Rs.{lots * abs(max_loss_per_lot):,}")

def guard_max_loss(strategy_max_loss, capital, hard_cap_pct=0.05):
    if abs(strategy_max_loss) > capital * hard_cap_pct:
        raise ValueError(f"strategy max loss {strategy_max_loss} exceeds hard cap {capital * hard_cap_pct}")
    return True

guard_max_loss(lots * abs(max_loss_per_lot), capital)
"""),
    ]


def body_16_oms():
    return [
        md("A thin OMS wrapper over a broker session routed through the static IP — plug in your broker's REST base URL and auth headers."),
        code("""class OrderManager:
    \"\"\"Place / modify / cancel orders through a ServLoci-proxied session.\"\"\"
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url.rstrip("/")

    def place(self, order: dict) -> dict:
        r = self.session.post(f"{self.base_url}/orders", json=order, timeout=8)
        r.raise_for_status()
        return r.json()

    def modify(self, order_id: str, changes: dict) -> dict:
        r = self.session.put(f"{self.base_url}/orders/{order_id}", json=changes, timeout=8)
        r.raise_for_status()
        return r.json()

    def cancel(self, order_id: str) -> dict:
        r = self.session.delete(f"{self.base_url}/orders/{order_id}", timeout=8)
        r.raise_for_status()
        return r.json()

if sl:
    oms = OrderManager(sl.session(), base_url=os.environ.get("BROKER_API_BASE", "https://api.example-broker.com/v1"))
    order = {"symbol": "NIFTY24800CE", "transaction_type": "BUY", "quantity": 75, "order_type": "MARKET", "product": "INTRADAY"}
    # resp = oms.place(order)   # uncomment once BROKER_API_BASE + broker auth headers are set
    print("OMS ready — set BROKER_API_BASE and auth headers, then uncomment oms.place(order)")
else:
    print("Demo mode — set SERVLOCI_API_SECRET above to build a live OrderManager.")
"""),
    ]


def body_17_paper_trading():
    return [
        md("An SMA-crossover signal over historical data (notebook 13), tracked as paper trades — no order dispatch yet, see notebook 18 for that."),
        code("""import pandas as pd

nifty = pd.read_csv("nifty_2y.csv", index_col=0, parse_dates=True)
nifty["sma_fast"] = nifty["Close"].rolling(10).mean()
nifty["sma_slow"] = nifty["Close"].rolling(30).mean()
nifty["signal"] = 0
nifty.loc[nifty["sma_fast"] > nifty["sma_slow"], "signal"] = 1
nifty.loc[nifty["sma_fast"] < nifty["sma_slow"], "signal"] = -1
nifty["position_change"] = nifty["signal"].diff().fillna(0)

trade_log = []
for date, row in nifty.dropna(subset=["sma_slow"]).iterrows():
    if row["position_change"] != 0:
        trade_log.append({"date": date, "signal": int(row["signal"]), "price": row["Close"]})

paper_trades = pd.DataFrame(trade_log)
print(f"{len(paper_trades)} paper trades generated")
paper_trades.tail()
"""),
    ]


def body_18_signal_pipeline():
    return [
        md("A poll → signal → dispatch skeleton. Swap `check_signal()` for your real source (indicator, model, webhook) and `oms` for a live `OrderManager` (notebook 16)."),
        code("""import time

def check_signal():
    \"\"\"Replace with your real signal source.\"\"\"
    return "BUY"  # | "SELL" | "HOLD"

def dispatch(signal, oms=None, dry_run=True):
    if signal == "HOLD":
        return None
    order = {"symbol": "NIFTY24800CE", "transaction_type": signal, "quantity": 75, "order_type": "MARKET", "product": "INTRADAY"}
    if dry_run or oms is None:
        print("[DRY RUN] would place:", order)
        return order
    return oms.place(order)

DRY_RUN = True  # flip to False only once OMS + credentials are wired and tested end-to-end
for _ in range(3):  # demo: 3 polls instead of an infinite loop
    dispatch(check_signal(), dry_run=DRY_RUN)
    time.sleep(1)
"""),
    ]


def body_19_capstone():
    return [
        md("Combines the SDK, an options template, risk-based sizing, and dry-run order dispatch into one runnable skeleton — the sum of notebooks 01, 10, 15, 16."),
        code("""import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("servloci-bot")

DRY_RUN = True

def nearest_strike(spot, step):
    return round(spot / step) * step

def iron_condor(spot, step, qty=1):
    atm = nearest_strike(spot, step)
    return [
        {"side": "sell", "type": "CE", "strike": atm + 2 * step, "qty": qty},
        {"side": "buy", "type": "CE", "strike": atm + 4 * step, "qty": qty},
        {"side": "sell", "type": "PE", "strike": atm - 2 * step, "qty": qty},
        {"side": "buy", "type": "PE", "strike": atm - 4 * step, "qty": qty},
    ]

def position_size(capital, risk_pct, max_loss_per_lot):
    if max_loss_per_lot <= 0:
        return 0
    return max(int((capital * risk_pct) // max_loss_per_lot), 0)

def run_once(spot, capital=500_000, risk_pct=0.02, assumed_max_loss_per_lot=4500):
    lots = position_size(capital, risk_pct, assumed_max_loss_per_lot)
    if lots == 0:
        log.warning("position size is 0 lots at current risk budget — skipping")
        return
    legs = iron_condor(spot, step=50, qty=lots)
    log.info("built iron condor: %s", legs)

    if sl is None:
        log.info("[DRY RUN — no SERVLOCI_API_SECRET] would dispatch %d lot(s)", lots)
        return

    session = sl.session()
    # oms = OrderManager(session, base_url=os.environ["BROKER_API_BASE"])   # from notebook 16
    for leg in legs:
        order = {
            "symbol": f"NIFTY{leg['strike']}{leg['type']}",
            "transaction_type": "BUY" if leg["side"] == "buy" else "SELL",
            "quantity": leg["qty"] * 75,
            "order_type": "MARKET",
            "product": "INTRADAY",
        }
        if DRY_RUN:
            log.info("[DRY RUN] would place: %s", order)
        else:
            pass  # oms.place(order)

run_once(spot=24000)
"""),
        md(f"That's the series. Recap: static IP (00) → SDK (01) → broker auth (02-05) → options math (06-10) → live data (11-12) → backtesting (13-14) → risk + execution (15-19).\n\nKeep building at [{SITE}/tools/strategy-builder]({SITE}/tools/strategy-builder), or grab your own static IP at [{SITE}/register]({SITE}/register)."),
    ]


# ── Notebook index ──────────────────────────────────────────────────────

NOTEBOOKS = [
    {"filename": "00_get_static_ip_and_verify.ipynb", "title": "Get Your Static IP & Verify It", "subtitle": "Claim a dedicated static IPv6 and confirm your egress IP actually changes.", "body": body_00_get_static_ip},
    {"filename": "01_servloci_sdk_quickstart.ipynb", "title": "ServLoci SDK Quickstart", "subtitle": "The four ways to use the `ServLoci` Python class.", "body": body_01_sdk_quickstart},
    {"filename": "02_broker_auth_zerodha_kite.ipynb", "title": "Broker Auth: Zerodha (Kite Connect)", "subtitle": "Authenticate and place a demo order via Kite Connect over your static IP.", "body": body_02_zerodha},
    {"filename": "03_broker_auth_dhan.ipynb", "title": "Broker Auth: Dhan", "subtitle": "Authenticate and place a demo order via DhanHQ v2 over your static IP.", "body": body_03_dhan},
    {"filename": "04_broker_auth_groww.ipynb", "title": "Broker Auth: Groww", "subtitle": "Authenticate and place a demo order via the Groww Trade API over your static IP.", "body": body_04_groww},
    {"filename": "05_broker_auth_fyers.ipynb", "title": "Broker Auth: Fyers", "subtitle": "Authenticate and place a demo order via the FYERS API over your static IP.", "body": body_05_fyers},
    {"filename": "06_black_scholes_pricing_greeks.ipynb", "title": "Black-Scholes Pricing & Greeks", "subtitle": "Option price, delta, gamma, theta, vega — ported from the site's pricer.", "body": body_06_black_scholes},
    {"filename": "07_option_payoff_breakeven_calculator.ipynb", "title": "Option Payoff & Breakeven Calculator", "subtitle": "Multi-leg payoff curves, breakevens, and max profit/loss at expiry.", "body": body_07_payoff_breakeven},
    {"filename": "08_strategy_straddle_strangle.ipynb", "title": "Strategy: Straddle & Strangle", "subtitle": "Long straddle, short straddle, and long strangle templates with payoff charts.", "body": body_08_straddle_strangle},
    {"filename": "09_strategy_vertical_spreads.ipynb", "title": "Strategy: Vertical Spreads", "subtitle": "Bull call spread and bear call spread templates with payoff charts.", "body": body_09_vertical_spreads},
    {"filename": "10_strategy_iron_condor.ipynb", "title": "Strategy: Iron Condor", "subtitle": "Four-leg range-bound strategy template with a payoff chart.", "body": body_10_iron_condor},
    {"filename": "11_live_option_chain_fetch.ipynb", "title": "Live Option Chain Fetch", "subtitle": "Pull live NIFTY/BANKNIFTY strikes from ServLoci's public option-chain endpoint.", "body": body_11_live_chain},
    {"filename": "12_implied_volatility_surface.ipynb", "title": "Implied Volatility Skew", "subtitle": "Back out per-strike IV from live premiums via bisection.", "body": body_12_iv_surface},
    {"filename": "13_historical_data_for_backtesting.ipynb", "title": "Historical Data for Backtesting", "subtitle": "Pull 2 years of NIFTY daily closes for the backtests that follow.", "body": body_13_historical_data},
    {"filename": "14_backtest_options_strategy.ipynb", "title": "Backtest: Weekly Short Straddle", "subtitle": "A simplified, cost-free backtest of a weekly ATM short straddle.", "body": body_14_backtest},
    {"filename": "15_position_sizing_risk_management.ipynb", "title": "Position Sizing & Risk Management", "subtitle": "Fixed-fractional lot sizing and a hard max-loss guardrail.", "body": body_15_position_sizing},
    {"filename": "16_order_management_system.ipynb", "title": "Order Management System", "subtitle": "Place, modify, and cancel orders through a ServLoci-proxied session.", "body": body_16_oms},
    {"filename": "17_paper_trading_loop.ipynb", "title": "Paper Trading Loop", "subtitle": "An SMA-crossover signal tracked as simulated paper trades.", "body": body_17_paper_trading},
    {"filename": "18_signal_to_order_pipeline.ipynb", "title": "Signal-to-Order Pipeline", "subtitle": "Poll a signal source and dry-run dispatch to an OMS.", "body": body_18_signal_pipeline},
    {"filename": "19_capstone_end_to_end_algo_bot.ipynb", "title": "Capstone: End-to-End Algo Bot", "subtitle": "SDK + strategy template + risk sizing + dry-run OMS dispatch, combined.", "body": body_19_capstone},
]

NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "name": "python3"},
    "language_info": {"name": "python"},
    "colab": {"provenance": [], "name": None},
}


def build_notebook(idx, entry):
    cells = (
        header_cells(idx, entry["filename"], entry["title"], entry["subtitle"])
        + setup_cells()
        + entry["body"]()
        + footer_cells(idx)
    )
    meta = dict(NB_METADATA)
    meta["colab"] = {"provenance": [], "name": entry["filename"]}
    return {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": meta,
        "cells": cells,
    }


def main():
    for idx, entry in enumerate(NOTEBOOKS):
        nb = build_notebook(idx, entry)
        path = os.path.join(OUT_DIR, entry["filename"])
        with open(path, "w") as f:
            json.dump(nb, f, indent=1)
            f.write("\n")
        print("wrote", entry["filename"])


if __name__ == "__main__":
    main()
