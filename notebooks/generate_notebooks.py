#!/usr/bin/env python3
"""Generates notebooks/*.ipynb — the ServLoci algo/options trading series.

Run: python notebooks/generate_notebooks.py
Regenerates the learning series and the standalone Colab Dhan quickstart.
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

Part {idx:02d} of {len(NOTEBOOKS)} in the [ServLoci algo/options trading notebook series]({SITE}/docs) — full index in `notebooks/README.md`.
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


def yfinance_setup_cells():
    text = """!pip install -q yfinance

import yfinance as yf
import pandas as pd
import numpy as np

# No broker account, no API key, no ServLoci setup needed for this chapter —
# yfinance reads public end-of-day data from Yahoo Finance. Indian tickers take
# an ".NS" suffix (NSE) or ".BO" (BSE); index tickers are prefixed with "^"
# (^NSEI = Nifty 50, ^BSESN = Sensex, ^GSPC = S&P 500).
NSE_TICKER = "RELIANCE.NS"
US_TICKER = "AAPL"
INDEX_TICKER = "^NSEI"

print("yfinance", yf.__version__)
"""
    return [md("## Setup — no broker account needed"), code(text)]


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

INDICATOR_ENGINE_SRC = r'''import numpy as np
import pandas as pd

def compute_top_50(frame):
    """Return 50 named indicators from an OHLCV DataFrame.

    Input columns are case-insensitive: open, high, low, close and volume.
    Warm-up rows contain NaN by design; never backfill them into a live signal.
    """
    df = frame.rename(columns={c: str(c).lower() for c in frame.columns}).copy()
    required = {"open", "high", "low", "close", "volume"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"missing OHLCV columns: {sorted(missing)}")
    o, h, l, c, v = (df[x].astype(float) for x in ("open", "high", "low", "close", "volume"))
    out = pd.DataFrame(index=df.index)
    safe = lambda x: x.replace([np.inf, -np.inf], np.nan)
    ema = lambda x, n: x.ewm(span=n, adjust=False, min_periods=n).mean()
    wma = lambda x, n: x.rolling(n).apply(
        lambda a: np.dot(a, np.arange(1, n + 1)) / (n * (n + 1) / 2), raw=True
    )

    # Trend and moving-average family (1-11)
    out["01_sma_20"] = c.rolling(20).mean()
    out["02_ema_20"] = ema(c, 20)
    out["03_wma_20"] = wma(c, 20)
    out["04_hma_20"] = wma(2 * wma(c, 10) - wma(c, 20), 4)
    e1 = ema(c, 20); e2 = ema(e1, 20); e3 = ema(e2, 20)
    out["05_dema_20"] = 2 * e1 - e2
    out["06_tema_20"] = 3 * e1 - 3 * e2 + e3
    out["07_vwma_20"] = safe((c * v).rolling(20).sum() / v.rolling(20).sum())
    macd = ema(c, 12) - ema(c, 26)
    out["08_macd"] = macd
    out["09_macd_signal"] = ema(macd, 9)
    out["10_ppo"] = safe(100 * macd / ema(c, 26))
    ex1 = ema(c, 15); ex2 = ema(ex1, 15); ex3 = ema(ex2, 15)
    out["11_trix"] = ex3.pct_change(fill_method=None) * 100

    # Momentum and oscillator family (12-24)
    out["12_roc_12"] = c.pct_change(12, fill_method=None) * 100
    out["13_momentum_10"] = c.diff(10)
    delta = c.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    out["14_rsi_14"] = 100 - (100 / (1 + safe(avg_gain / avg_loss)))
    low14, high14 = l.rolling(14).min(), h.rolling(14).max()
    stoch = safe(100 * (c - low14) / (high14 - low14))
    out["15_stochastic_k"] = stoch
    out["16_stochastic_d"] = stoch.rolling(3).mean()
    out["17_williams_r"] = safe(-100 * (high14 - c) / (high14 - low14))
    typical = (h + l + c) / 3
    tp_mean = typical.rolling(20).mean()
    mean_dev = typical.rolling(20).apply(lambda a: np.mean(np.abs(a - a.mean())), raw=True)
    out["18_cci_20"] = safe((typical - tp_mean) / (0.015 * mean_dev))
    prev = c.shift(1)
    buy_pressure = c - pd.concat([l, prev], axis=1).min(axis=1)
    true_range = pd.concat([h - l, (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    out["19_ultimate_oscillator"] = safe(100 * (
        4 * buy_pressure.rolling(7).sum() / true_range.rolling(7).sum()
        + 2 * buy_pressure.rolling(14).sum() / true_range.rolling(14).sum()
        + buy_pressure.rolling(28).sum() / true_range.rolling(28).sum()
    ) / 7)
    midpoint = (h + l) / 2
    out["20_awesome_oscillator"] = midpoint.rolling(5).mean() - midpoint.rolling(34).mean()
    r1, r2, r3, r4 = (c.pct_change(n, fill_method=None) * 100 for n in (10, 15, 20, 30))
    out["21_kst"] = r1.rolling(10).sum() + 2*r2.rolling(10).sum() + 3*r3.rolling(10).sum() + 4*r4.rolling(15).sum()
    pc = c.diff(); apc = pc.abs()
    out["22_tsi"] = safe(100 * ema(ema(pc, 25), 13) / ema(ema(apc, 25), 13))
    streak = pd.Series(0.0, index=c.index)
    for i in range(1, len(c)):
        direction = np.sign(c.iloc[i] - c.iloc[i - 1])
        prior = streak.iloc[i - 1]
        streak.iloc[i] = 0 if direction == 0 else direction * (abs(prior) + 1 if np.sign(prior) == direction else 1)
    def rsi_series(x, n):
        d = x.diff(); g = d.clip(lower=0).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
        q = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
        return 100 - 100 / (1 + safe(g / q))
    pct_rank = c.pct_change(fill_method=None).rolling(100).apply(lambda a: 100 * (a[-1] > a[:-1]).mean(), raw=True)
    out["23_connors_rsi"] = (rsi_series(c, 3) + rsi_series(streak, 2) + pct_rank) / 3
    sum_gain, sum_loss = gain.rolling(14).sum(), loss.rolling(14).sum()
    out["24_cmo_14"] = safe(100 * (sum_gain - sum_loss) / (sum_gain + sum_loss))

    # Volatility and channel family (25-36)
    mid = c.rolling(20).mean(); std = c.rolling(20).std(ddof=0)
    upper, lower = mid + 2*std, mid - 2*std
    out["25_bollinger_upper"] = upper
    out["26_bollinger_lower"] = lower
    out["27_bollinger_bandwidth"] = safe(100 * (upper - lower) / mid)
    atr = true_range.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    out["28_atr_14"] = atr
    out["29_natr_14"] = safe(100 * atr / c)
    out["30_true_range"] = true_range
    kel_mid = ema(c, 20)
    out["31_keltner_upper"] = kel_mid + 2 * atr
    out["32_keltner_lower"] = kel_mid - 2 * atr
    out["33_donchian_upper"] = h.rolling(20).max()
    out["34_donchian_lower"] = l.rolling(20).min()
    out["35_stddev_20"] = std
    out["36_historical_volatility"] = np.log(c / c.shift(1)).rolling(20).std(ddof=0) * np.sqrt(252) * 100

    # Directional, stop and cloud family (37-46)
    up_move, down_move = h.diff(), -l.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    plus_di = safe(100 * plus_dm.ewm(alpha=1/14, adjust=False, min_periods=14).mean() / atr)
    minus_di = safe(100 * minus_dm.ewm(alpha=1/14, adjust=False, min_periods=14).mean() / atr)
    out["37_adx_14"] = safe(100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    out["38_plus_di"] = plus_di
    out["39_minus_di"] = minus_di
    out["40_aroon_up"] = h.rolling(25).apply(lambda a: 100 * (np.argmax(a) + 1) / len(a), raw=True)
    out["41_aroon_down"] = l.rolling(25).apply(lambda a: 100 * (np.argmin(a) + 1) / len(a), raw=True)
    out["42_vortex_plus"] = safe((h - l.shift(1)).abs().rolling(14).sum() / true_range.rolling(14).sum())
    out["43_vortex_minus"] = safe((l - h.shift(1)).abs().rolling(14).sum() / true_range.rolling(14).sum())
    psar = pd.Series(np.nan, index=c.index)
    if len(c):
        bull, af, extreme = True, 0.02, h.iloc[0]
        psar.iloc[0] = l.iloc[0]
        for i in range(1, len(c)):
            candidate = psar.iloc[i-1] + af * (extreme - psar.iloc[i-1])
            if bull:
                candidate = min(candidate, l.iloc[i-1], l.iloc[max(i-2, 0)])
                if l.iloc[i] < candidate: bull, candidate, af, extreme = False, extreme, 0.02, l.iloc[i]
                elif h.iloc[i] > extreme: extreme, af = h.iloc[i], min(af + 0.02, 0.2)
            else:
                candidate = max(candidate, h.iloc[i-1], h.iloc[max(i-2, 0)])
                if h.iloc[i] > candidate: bull, candidate, af, extreme = True, extreme, 0.02, h.iloc[i]
                elif l.iloc[i] < extreme: extreme, af = l.iloc[i], min(af + 0.02, 0.2)
            psar.iloc[i] = candidate
    out["44_parabolic_sar"] = psar
    out["45_ichimoku_conversion"] = (h.rolling(9).max() + l.rolling(9).min()) / 2
    out["46_ichimoku_base"] = (h.rolling(26).max() + l.rolling(26).min()) / 2

    # Volume and money-flow family (47-50)
    out["47_obv"] = (np.sign(c.diff()).fillna(0) * v).cumsum()
    raw_money = typical * v; positive = raw_money.where(typical.diff() > 0, 0); negative = raw_money.where(typical.diff() < 0, 0)
    out["48_mfi_14"] = 100 - 100 / (1 + safe(positive.rolling(14).sum() / negative.rolling(14).sum()))
    money_flow_multiplier = safe(((c - l) - (h - c)) / (h - l))
    money_flow_volume = money_flow_multiplier * v
    out["49_cmf_20"] = safe(money_flow_volume.rolling(20).sum() / v.rolling(20).sum())
    out["50_accumulation_distribution"] = money_flow_volume.fillna(0).cumsum()
    assert out.shape[1] == 50
    return out
'''


# ── Per-notebook bodies ──────────────────────────────────────────────────

def body_00_get_static_ip():
    return [
        md("""## Why algo trading needs a static IP at all

Every Indian broker that exposes an order-placement API — Zerodha's Kite Connect,
DhanHQ, Groww's Trade API, FYERS — ties API keys to a small allowlist of source
IPs. This is not a broker being difficult: SEBI's algo-trading framework and each
exchange's colocation/API rules push brokers to bind trading credentials to a
known, auditable network origin, the same way a bank binds a corporate API key
to a fixed egress IP. An API key plus a secret is enough to authenticate; the IP
allowlist is the second control that limits *where* that authentication is
allowed to come from, so a leaked key alone can't be used to place orders from
an arbitrary machine.

That's exactly what makes a laptop, a home router, or a notebook running on
Google Colab unsuitable for this without help. Home and mobile ISPs mostly hand
out **dynamic** IPs that rotate on reconnect — the address your broker
allowlisted yesterday may not be the one you have today. Colab's outbound IP is
worse: it's drawn from a shared Google Cloud pool, reused across unrelated
users and sessions, and frequently already present on abuse blocklists, so even
if you could allowlist it, the next runtime restart would hand you a different
one anyway.

A **static IP** fixes the address side of the problem: it's an IP that's yours,
doesn't change between sessions, and can be allowlisted once. The cell below
proves the concept end to end — it prints Colab's own (unusable) address, then
the address your broker will actually see once traffic is routed through a
static IPv6 assigned to your account. That second address is your **egress
IP**: the IP the *destination server* (the broker's API) observes as the
origin of the request, after any proxying in front of it. Whitelisting is
always done against the egress IP, never against the IP your notebook happens
to be running on."""),
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
        md("""IPv6 rather than IPv4 matters here mainly for supply: IPv4 addresses are
scarce and expensive to dedicate one-per-user, while IPv6 has enough address
space to hand every account a permanent, non-shared address. Most Indian
broker API consoles accept IPv6 allowlist entries directly; a handful still
ask for a fallback IPv4, which is why some brokers (see notebooks 02-05)
support both.

Next: whitelist the printed IPv6 in your broker's API console (see notebooks
02-05 for the per-broker steps), then move on to the SDK quickstart to see how
that same address gets applied automatically to every broker call you make
from Python."""),
    ]


def body_01_sdk_quickstart():
    return [
        md("""## Two ways to route traffic, and why the difference matters

A `requests.Session` (and the connection pool underneath it) is created once
and reused for every call made through it — brokers' Python SDKs each build
one internally the moment you import them. That means *when* you enable a
proxy relative to that import is not cosmetic; it decides whether the
broker's own HTTP calls ever see it.

The SDK gives you two strategies for that reason:

- **Scoped**: `session()` returns a fresh `requests.Session` with the proxy
  already set. Use it for your own `requests` calls; it never touches code you
  don't own.
- **Process-wide**: `attach()` monkey-patches `requests.Session.__init__` so
  that *every* session created afterwards — including the one a broker SDK
  builds internally on import — picks up the proxy automatically. This is the
  only way to route a third-party SDK's traffic without editing its source.

`proxy_url()` / `proxies()` and `export_env()` exist for tools that don't use
`requests` at all — a raw `curl`, an `httpx` client, or any process that reads
standard `HTTP_PROXY`/`HTTPS_PROXY` environment variables."""),
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
        md("""`attach()` must run **before** you import a broker SDK — dhanhq, kiteconnect,
growwapi and fyers-apiv3 all create a `requests.Session` at import time, so
patching afterwards is a no-op for their traffic even though it still works
for your own. The one-liner `servloci.configure(api_key, api_secret)` does
`ServLoci(...).attach()` in a single call, and is the pattern used in
notebooks 02-05 below."""),
    ]


def _broker_body(name, pip_pkg, support_note, auth_note, snippet):
    return [
        md(f"**Support level:** {support_note}"),
        md(auth_note),
        code(f"""if sl:
    sl.attach()  # BEFORE importing {pip_pkg} — it creates a requests.Session at import time
{snippet}
else:
    print("Demo mode — set SERVLOCI_API_SECRET above to run this against your {name} account.")
"""),
        md(f"Install the broker SDK separately: `!pip install -q {pip_pkg}`. Full whitelist steps: [{SITE}/docs/brokers]({SITE}/docs)."),
    ]


BROKER_AUTH_FLOW = """Indian broker APIs authenticate trading sessions with an OAuth-style
two-step handshake, not a single long-lived key. You redirect the user (in
practice, yourself) to a broker login page, the broker redirects back with a
short-lived `request_token`, and you exchange that token — together with your
app's `api_secret` — for an `access_token` that's valid for actual order
calls. The `api_key`/`api_secret` pair identifies *your app*; the
`access_token` identifies *an authenticated session* and, at every broker
covered here, expires at end of trading day regardless of activity. That
forced daily re-login is a deliberate session-security control, common across
SEBI-regulated broker APIs, so a stolen access token has a shelf life measured
in hours, not indefinitely."""


def body_02_zerodha():
    return _broker_body(
        "Zerodha",
        "kiteconnect",
        "Self-service — Kite Connect apps are approved instantly from the developer console; add your ServLoci IPv6 there.",
        BROKER_AUTH_FLOW + """

Kite Connect is the most self-service of the four: app creation, API key
issuance, and IP allowlisting all happen immediately in the developer console,
with no manual review step. That makes it a common first choice for testing
an integration, though the API itself carries a separate subscription fee
independent of brokerage.""",
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
        BROKER_AUTH_FLOW + """

DhanHQ trades the Kite-style instant approval for a support-reviewed
onboarding: API access and IP allowlisting are both requested through a
ticket rather than granted automatically. In exchange, DhanHQ bundles API
access with the trading account at no separate subscription fee, which is why
it's the broker used for the full restart-safe Colab walkthrough later in
this series.""",
        """    from dhanhq import dhanhq

    dhan = dhanhq(client_id=os.environ.get("DHAN_CLIENT_ID", ""), access_token=os.environ.get("DHAN_ACCESS_TOKEN", ""))
    print("Dhan client ready:", dhan.client_id)
    # order = dhan.place_order(security_id="1333", exchange_segment=dhan.NSE, transaction_type=dhan.BUY,
    #                           quantity=1, order_type=dhan.MARKET, product_type=dhan.INTRA, price=0)""",
    )


def build_colab_dhan_notebook():
    """A restart-safe, top-to-bottom Colab notebook for DhanHQ 2.2."""
    filename = "colab_dhan_trading_static_ip.ipynb"
    cells = [
        md(f"""# DhanHQ on Google Colab with a ServLoci static IP

{colab_badge(filename)}

Run these cells from top to bottom. The notebook installs dependencies before
enabling the broker-only route, reads credentials from **Colab Secrets**, verifies
the assigned IPv6, creates a DhanHQ 2.2 client, and performs one read-only API call.

Create these secrets in Colab's key icon before running:

- `STATIC_IP_TOKEN` — the latest `sl_live_...` token from the ServLoci portal
- `DHAN_CLIENT_ID` — your Dhan client ID
- `DHAN_ACCESS_TOKEN` — your current Dhan access token

Grant this notebook access to all three secrets. No secret value is printed.
"""),
        md("## 1. Clear stale version 0.3.0 notebook state"),
        code("""import os
import sys

SMOKE_TEST = "--smoke" in sys.argv  # used only by the automated Colab CLI test
PROXY_KEYS = (
    "ALL_PROXY", "all_proxy",
    "HTTP_PROXY", "http_proxy",
    "HTTPS_PROXY", "https_proxy",
)

# A rerun after trading-static-ip 0.3.0 may retain both monkey patches and
# proxy variables. Undo them before pip contacts pypi.org/simple/*.
if "servloci" in sys.modules:
    try:
        sys.modules["servloci"].unconfigure()
    except Exception:
        pass

for key in PROXY_KEYS:
    if "comm.servloci.in:1080" in os.environ.get(key, ""):
        os.environ.pop(key, None)

assert not any("comm.servloci.in:1080" in os.environ.get(k, "") for k in PROXY_KEYS)
print("Clean start: package installation will use Colab's direct connection.")
"""),
        md("## 2. Install the fixed SDK and DhanHQ"),
        code("""import subprocess

subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q", "--upgrade",
    "trading-static-ip==0.3.1", "dhanhq==2.2.0",
])
print("Dependencies installed.")
"""),
        md("## 3. Load Colab Secrets"),
        code("""import importlib
import servloci

# Handles a deliberate top-to-bottom rerun without requiring another runtime restart.
servloci = importlib.reload(servloci)
assert servloci.__version__ == "0.3.1", servloci.__version__

if SMOKE_TEST:
    STATIC_IP_TOKEN = "sl_live_colab_cli_smoke_test"
    DHAN_CLIENT_ID = "1000000000"
    DHAN_ACCESS_TOKEN = "dhan_cli_smoke_test"
else:
    from google.colab import userdata

    def required_secret(name):
        value = userdata.get(name)
        if not value:
            raise ValueError(f"Missing Colab secret: {name}")
        return value.strip()

    STATIC_IP_TOKEN = required_secret("STATIC_IP_TOKEN")
    DHAN_CLIENT_ID = required_secret("DHAN_CLIENT_ID")
    DHAN_ACCESS_TOKEN = required_secret("DHAN_ACCESS_TOKEN")
    if not STATIC_IP_TOKEN.startswith("sl_live_"):
        raise ValueError("STATIC_IP_TOKEN must be the latest sl_live_... portal token")

print("Secrets loaded without displaying their values.")
"""),
        md("## 4. Record Colab's direct IP, then enable ServLoci"),
        code("""import requests

direct_ip = None
if not SMOKE_TEST:
    direct_ip = requests.get("https://api.ipify.org", timeout=20).text.strip()
    print("Direct Colab IP:", direct_ip)

route = servloci.configure(
    token=STATIC_IP_TOKEN,
    broker="dhan",
)

# 0.3.1 patches requests/HTTPX without leaking SOCKS settings to pip subprocesses.
assert not any("comm.servloci.in:1080" in os.environ.get(k, "") for k in PROXY_KEYS)
print("ServLoci transport enabled for Dhan; pip remains direct.")
"""),
        md("## 5. Verify the assigned static IPv6"),
        code("""import ipaddress

if SMOKE_TEST:
    print("Colab CLI smoke mode: live token/IP check skipped.")
else:
    static_ip = requests.get("https://api.ipify.org", timeout=20).text.strip()
    parsed = ipaddress.ip_address(static_ip)
    assert parsed.version == 6, f"Expected the assigned IPv6, received {static_ip}"
    assert static_ip != direct_ip, "ServLoci route did not change the observed IP"
    print("ServLoci static IPv6:", static_ip)
"""),
        md("## 6. Create the DhanHQ 2.2 client"),
        code("""# DhanHQ 2.2 uses DhanContext; older keyword-only examples no longer apply.
from dhanhq import DhanContext, dhanhq

dhan_context = DhanContext(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
dhan = dhanhq(dhan_context)

# DhanHQ created its own requests.Session after configure(), so its internal
# HTTPS calls are transparently routed through the ServLoci static IP.
assert dhan.dhan_http.session is not None
print("DhanHQ client ready through ServLoci.")
"""),
        md("## 7. Run a safe, read-only Dhan call"),
        code("""if SMOKE_TEST:
    print("Colab CLI smoke mode: authenticated Dhan call skipped.")
else:
    result = dhan.get_fund_limits()
    status = result.get("status") if isinstance(result, dict) else None
    if status != "success":
        raise RuntimeError(f"Dhan read-only call failed: {result.get('remarks', result)}")
    print("Dhan read-only call succeeded. Response data is intentionally hidden.")
"""),
        md("## 8. Optional order template — dry run only"),
        code("""order = {
    "security_id": "1333",       # example only; verify the current instrument ID
    "exchange_segment": dhan.NSE,
    "transaction_type": dhan.BUY,
    "quantity": 1,
    "order_type": dhan.MARKET,
    "product_type": dhan.INTRA,
    "price": 0,
}

DRY_RUN = True
if DRY_RUN:
    print("DRY RUN — no order sent:", order)
else:
    raise RuntimeError("Review risk, symbol, quantity, and market status before enabling live orders.")
"""),
        md("""## Finished

Your DhanHQ `requests.Session` is now routed through the assigned ServLoci IPv6.
Keep `DRY_RUN = True` until you have separately validated permissions, instrument
IDs, quantities, risk limits, and the broker's current order fields.

When you are finished with broker traffic, restore normal transports with:

```python
servloci.unconfigure()
```
"""),
    ]
    meta = dict(NB_METADATA)
    meta["colab"] = {"provenance": [], "name": filename}
    return {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": meta,
        "cells": cells,
    }


def body_04_groww():
    return _broker_body(
        "Groww",
        "growwapi",
        "Support-confirmed workflow — Groww enables Trade API access per-account after a confirmation email; include your ServLoci IP in that thread.",
        BROKER_AUTH_FLOW + """

Groww's Trade API is the newest of the four and leans on account-linked
confirmation rather than a developer console: access is switched on
per-account after a confirmation email, and the same email thread is where
you supply the static IP to allowlist. Worth knowing before you build against
it: order and market-data coverage is still narrower than the older APIs, so
check the current feature list against what your strategy needs.""",
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
        BROKER_AUTH_FLOW + """

FYERS sits between Kite's instant self-service and Dhan's ticket queue: API
access is enabled per app, but support verifies the requesting IP before
switching it on, including for family/sub-accounts trading under one
umbrella. FYERS also publishes a WebSocket feed alongside the REST API, which
matters once you move from polling (notebook 11) to a lower-latency data
path.""",
        """    from fyers_apiv3 import fyersModel

    fyers = fyersModel.FyersModel(client_id=os.environ.get("FYERS_CLIENT_ID", ""),
                                   token=os.environ.get("FYERS_ACCESS_TOKEN", ""), is_async=False)
    print("Fyers client ready")
    # order = fyers.place_order(data={"symbol": "NSE:INFY-EQ", "qty": 1, "type": 2,
    #                                  "side": 1, "productType": "INTRADAY"})""",
    )


def body_06_black_scholes():
    return [
        md("""## Why option pricing needs a model

A stock has one obvious "fair value" input: the price someone will pay for it right now. An option doesn't — its value depends on where the underlying *might* go before expiry, how much time is left, and how uncertain the market is about that path. Black-Scholes (1973) was the first widely-used formula to turn those inputs — spot, strike, time to expiry, volatility, and the risk-free rate — into a single price, and it's still the reference model every Indian index-options trader is quoted against, even when the market's own price has drifted from it.

Python port of `shared/lib/blackScholes.js` — the exact pricer behind `/tools/strategy-builder`, swapping the hand-rolled `erf` approximation for `scipy.stats.norm`."""),
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
        md("""## Reading the Greeks like a trader, not a mathematician

- **Delta** is the option's directional exposure — an ATM call near 0.5 delta behaves like half a share; a deep ITM call near 1.0 behaves like a full share. Traders use delta as a rough hedge ratio ("I'm short 3 lots at 0.4 delta, so I'm short the equivalent of ~1.2 lots of the underlying") and as a proxy for probability-of-finishing-ITM.
- **Gamma** measures how fast delta itself moves. Gamma is highest for ATM options in the final days before expiry — this is why weekly index-option sellers get nervous into expiry day: a small spot move near the strike can flip an option's delta (and the position's effective exposure) very quickly, which is the mechanism behind "gamma risk" blowups.
- **Theta** is time decay, quoted per day. It's the reason option *selling* is a business model on its own: every day that passes without the underlying moving, a short option collects theta as pure carry — as long as gamma doesn't overwhelm it first.
- **Vega** is exposure to implied volatility itself, independent of direction. Buying an option before an event (RBI policy, results, budget day) is often a bet on vega — IV expands going in — followed by the well-known "IV crush" once the event passes and uncertainty resolves.

Black-Scholes assumes continuous trading, a constant known volatility, and log-normal returns — none of which hold exactly for NSE index options. In practice: volatility is not constant across strikes (see notebook 12's IV skew), gaps happen overnight and around events (violating the "continuous price path" assumption), and the model has no view on liquidity or bid-ask spread. Traders use Black-Scholes as a common quoting language, not as ground truth — the market's own price, not the model's, is what you actually pay or receive."""),
    ]


def body_07_payoff_breakeven():
    return [
        md("""## Payoff at expiry vs. mark-to-market P&L

Everything in this notebook is the payoff **at expiry** — intrinsic value only, ignoring time value and any premium you could realize by closing early. That's a deliberate simplification: it's the easiest way to see a strategy's worst case and best case, but it is *not* what your broker terminal shows you intraday, where the P&L also reflects theta already collected/paid and any change in implied volatility. Two positions with the same expiry payoff can have very different mark-to-market P&L on day 3 of a 7-day trade.

**Breakeven** is the underlying price at which net P&L crosses zero — for a single long call, that's strike + premium paid, not the strike itself. It's easy to forget the premium and think of the strike as the breakeven; the two only coincide for a position with zero net cost.

**Max profit/loss** matters beyond curiosity — your broker's margin requirement, and any risk-management guardrail you build (see notebook 15), should be sized off the realistic worst case for the *combination* of legs, not each leg in isolation. A defined-risk spread and a naked short option can have identical initial margin but wildly different max loss.

Python port of `shared/lib/strategyMath.js` — payoff is computed **at expiry** (intrinsic value only), same as the payoff chart on `/tools/strategy-builder`."""),
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
        md("""## Betting on volatility itself, not direction

A straddle or strangle is a bet on how *much* the underlying moves, not which way. That makes it fundamentally different from the vertical spreads in the next notebook, which express a directional view.

- **Long straddle** (buy ATM call + buy ATM put): you profit if the move — in either direction — is bigger than the combined premium paid. Traders reach for this ahead of a known catalyst (results, a policy announcement, an election outcome) when they expect a large move but don't know which way. The risk is capped at the premium paid, but IV is usually already elevated going into the event, so you're paying up for that uncertainty — and if the move doesn't happen, both legs decay together.
- **Short straddle** (sell ATM call + sell ATM put): the mirror position, collecting premium on the belief that the underlying will stay range-bound. This is a genuinely popular income strategy on NIFTY/BANKNIFTY weeklies because theta decay is fast into expiry — but the risk is **undefined on both sides**. A short straddle has no built-in stop; a sharp move against either leg can lose far more than the premium collected, which is why position sizing (notebook 15) and a hard max-loss guardrail matter more here than almost anywhere else in this series.
- **Long strangle**: the same volatility bet as a long straddle, using OTM strikes instead of ATM. Lower premium outlay, but the underlying has to move further before you're profitable — a real tradeoff between cost and breakeven width, not a strictly better version of the straddle.

The common thread: straddles and strangles are trades on **implied volatility versus realized volatility**. If you buy one and realized volatility turns out lower than what you paid for, you lose even if you correctly predicted the direction of the eventual move — timing matters as much as the thesis.

Port of the `long_straddle` / `short_straddle` / `long_strangle` templates from `shared/data/strategyTemplates.js`. Premiums are backfilled with Black-Scholes (notebook 06) since no live chain is passed in demo mode — swap in a real chain from notebook 11 for live premiums."""),
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
        md("""## Directional views with a capped price tag

A vertical spread — buy one strike, sell another strike of the same type and expiry — is how most traders express "I think it goes up (or down), but I want to know my exact worst case before I enter." Compare that to a naked long call: unlimited upside, but you're also paying full premium and full theta decay for it. Selling the further strike against your long reduces both the cost and the decay, at the price of capping the upside.

- **Bull call spread** (buy lower strike call, sell higher strike call): a moderately bullish trade. Max loss is the net premium paid; max profit is the strike width minus that premium. You'd choose this over an outright long call when you want to lower cost/theta exposure and you don't need unlimited upside — you have a target level in mind, not an open-ended one.
- **Bear call spread** (sell lower strike call, buy higher strike call): a credit spread — you collect premium up front, betting the underlying stays *below* the strike you sold. This is a defined-risk way to be bearish (or neutral-to-bearish) without the undefined risk of a naked short call; the long call you bought caps how much you can lose if you're wrong.

The strike width you choose is a direct dial on the risk/reward and the required margin: a wider spread has a bigger max profit and max loss (and needs more margin); a narrower spread is cheaper and safer but caps the reward tighter. There's no "correct" width — it's a function of your conviction and how much of your capital you're willing to allocate to a single view.

Port of `bull_call_spread` / `bear_call_spread` from `shared/data/strategyTemplates.js` — capped-risk directional strategies."""),
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
        md("""## A short straddle, with the tail risk capped

An iron condor is best understood as a short strangle (sell an OTM call and an OTM put, collecting premium on the belief the underlying stays range-bound) with a cheaper, further-OTM call and put bought on each side purely to cap the loss — turning two legs of undefined risk (notebook 08's short straddle problem) into four legs of defined risk. That's the whole trade: two vertical spreads, one on the call side, one on the put side, sold at the same time.

- **Max profit** is the net premium collected, realized if the underlying finishes between the two short strikes at expiry.
- **Max loss** is capped at the width of either spread minus the premium collected — known in advance, unlike a short strangle.
- **The common failure mode** isn't the "small daily moves" volatility that condors are built for — it's a strong, sustained trend that pushes price through one of the short strikes and keeps going. Because the position collects a relatively small premium against a much wider max loss, a single bad expiry can erase many prior weeks of small wins; this is the classic "picking up pennies in front of a steamroller" pattern traders warn about with range-bound selling strategies.

Because it's built from two verticals, everything from notebook 09 about strike-width tradeoffs applies to each side independently — you can make the condor asymmetric (wider on one side than the other) if your view is range-bound but skewed.

Port of `iron_condor` from `shared/data/strategyTemplates.js` — sell the near wings, buy the far wings, profit if price stays range-bound."""),
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
        md("""## Reading an option chain

An option chain lists, for every traded **strike** of an underlying, the call (`CE`) and put (`PE`) contract at that strike — its last traded price (LTP), bid/ask, and open interest (OI). Three things matter before you use one:

- **Moneyness.** A strike is *at-the-money* (ATM) if it's closest to spot, *in-the-money* (ITM) if exercising it now would be profitable (call strike below spot, put strike above spot), and *out-of-the-money* (OTM) otherwise. Most retail activity clusters within a few strikes either side of ATM.
- **Open interest as a crowding signal.** OI is the count of contracts still open at a strike, not traded volume. Large OI at a strike is read informally as a support/resistance level — a lot of capital has a stake in price not crossing it — but it's a crowd signal, not a law of physics; large OI can and does get blown through.
- **Bid-ask spread as a liquidity check.** A wide spread relative to LTP means slippage on entry/exit will eat into any edge the strategy has. Illiquid far-OTM strikes routinely have spreads worse than 5-10% of premium — always check spread before sizing a trade, not just the mid price.

No proxy needed for this one — this hits ServLoci's own public option-chain endpoint (5s server-side cache), the same one `/tools/strategy-builder` uses."""),
        code("""import requests

resp = requests.get("https://comm.servloci.in/api/market/option-chain", params={"symbol": "NIFTY"}, timeout=10)
resp.raise_for_status()
data = resp.json()
spot, chain = data.get("spot"), data.get("strikes", [])
print("Spot:", spot, "| strikes returned:", len(chain))
chain[:5]
"""),
        md("`chain` is shaped `[{strike, ce: {ltp, ...}, pe: {ltp, ...}}, ...]` — pass it straight into the `find_premium()` / template builders from notebooks 08-10 for real (not Black-Scholes-estimated) premiums. Before trusting a strike's premium, glance at its bid-ask spread and OI in the raw response — a tight theoretical payoff chart built on an illiquid strike is not a tradeable one."),
    ]


def body_12_iv_surface():
    return [
        md("""## What implied volatility actually is

Black-Scholes takes volatility as an *input* and produces a price. Implied volatility (IV) runs that backwards: given the price the market is actually paying for an option, what volatility assumption would make the model agree? There's no closed-form inverse for that, so it's solved numerically — bisection here, searching for the vol that reprices the option to match its observed premium.

IV is best read as **the market's forecast of future realized volatility over the option's remaining life**, expressed in price rather than in a probability. It is not a measurement of past price movement (that's realized/historical vol, notebook 13) — it's a forward-looking, and often wrong, consensus.

**Why IV differs by strike (skew).** If Black-Scholes were literally true, every strike on the same underlying and expiry would imply the same volatility. In practice they don't — equity index options typically show a downward-sloping "skew," where OTM puts carry higher IV than OTM calls. That's the market pricing in a fatter left tail: crashes happen faster than rallies, so demand for downside protection (buying puts) bids up their implied vol relative to the model's flat-vol assumption. Reading a skew chart: a steep negative slope going into OTM puts signals the market is currently paying up for crash insurance; a flat chain suggests complacency.

Backs out implied volatility per strike via bisection against the Black-Scholes pricer (notebook 06), using live chain LTPs (notebook 11) — a rough call-side skew, not a full surface (single expiry assumption below)."""),
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
        md("""## Why the data matters as much as the strategy

Every backtest is only as trustworthy as the data feeding it. Three traps show up constantly with retail backtests:

- **Corporate actions and index reconstitution.** Index levels (like NIFTY) get rebalanced periodically — constituents change, weights change. A price series that doesn't handle this consistently can show artificial gaps or drift that has nothing to do with market behavior.
- **Missing or misaligned sessions.** Exchange holidays, special trading sessions (muhurat trading), and half-days need to line up with your strategy's calendar logic, or a "Monday entry" rule can silently fire on the wrong day.
- **Look-ahead bias from adjusted data.** Adjusted close prices bake in future information (like a stock split announced later) into historical rows. Using adjusted data naively can make a strategy look like it "knew" something it couldn't have known at the time. For an index like NIFTY this specific trap doesn't apply directly, but it's the single most common way retail backtests silently cheat.

**Why 2 years.** A weekly options strategy trades roughly 50 times a year — 2 years gives on the order of 100 trades, enough to see the strategy across a few different volatility regimes (calm stretches, at least one shock) without pretending 100 data points is statistically bulletproof. Treat any conclusion from this sample size as a hypothesis, not a proven edge — the backtest notebook that follows says this again, because it's worth repeating.

Pulls historical NIFTY closes for the backtesting notebooks that follow. No ServLoci proxy needed — Yahoo Finance is publicly reachable."""),
        code("""!pip install -q yfinance
import yfinance as yf

nifty = yf.download("^NSEI", period="2y", interval="1d", progress=False, multi_level_index=False)
nifty.to_csv("nifty_2y.csv")
print(nifty.tail())
"""),
        md("`nifty_2y.csv` is reused by notebooks 14 and 17 — re-run this cell first if you're opening those standalone."),
    ]


def body_14_backtest():
    return [
        md("""## Backtesting is easy to get wrong in ways that flatter the strategy

A backtest answers "what would have happened" — it only becomes evidence of a real edge if the simulation avoids a short list of well-known ways to cheat, mostly by accident:

- **Look-ahead bias.** Using information that wouldn't have been available at the time of the trade — e.g. sizing today's position off a volatility figure computed with tomorrow's close. This backtest uses a 20-day *rolling* realized vol computed only from prior closes, which avoids the obvious version of this bug, but always audit every input a strategy touches for this.
- **Survivorship bias.** Testing only on instruments that still exist today (and dropping ones that were delisted or went to zero) makes strategies look better than they were, because the losers are missing from the sample. Less relevant for a single continuous index like NIFTY, very relevant the moment you backtest a stock-picking strategy over a universe.
- **Ignoring costs.** Real trades pay the bid-ask spread, brokerage, exchange transaction charges, and in India, STT (securities transaction tax) — which on options is charged on the sell side and is not trivial for high-frequency weekly strategies. A strategy that's profitable before costs can easily be a loser after them.
- **Overfitting to one historical window.** Tuning strike selection, entry day, or holding period until this specific 2-year window looks good is curve-fitting, not strategy design. The fix is out-of-sample or walk-forward testing — train assumptions on one period, validate on a period the tuning never saw — which this notebook does not do.

**Illustrative only** — no slippage, costs, or margin, and no out-of-sample split. Sells a weekly ATM straddle every Monday, priced with 20-day realized vol via Black-Scholes (notebook 06), held to Friday's close. Treat the P&L number below as a sanity check on the mechanics, not as a claim that this strategy makes money."""),
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
        md("""## Position sizing is risk management, not a math afterthought

**Fixed-fractional sizing** risks a fixed percentage of current capital on each trade rather than a fixed number of lots. It's simple, but it does the one thing that matters most: it makes the size of a loss scale down automatically as capital shrinks, instead of a fixed lot count taking a proportionally bigger bite out of a smaller account after a losing streak.

**Why a hard max-loss cap matters more than expected-value math.** A strategy can have positive expected value over hundreds of trades and still blow up an account on a single oversized position — this is the "risk of ruin" problem. Expected value is an average over a distribution; ruin is about the tail of that distribution, and a large enough single loss removes you from the game before the average has a chance to play out. That's why `guard_max_loss` below is a hard `raise`, not a warning — a guardrail that can be silently ignored under pressure (in a live, moving market) is not a guardrail.

**The psychological half of sizing.** Position size that's mathematically "correct" but larger than a trader is emotionally prepared to lose tends to produce panic exits at the worst possible moment — which turns a manageable drawdown into a realized loss. Sizing conservatively enough to sit through a strategy's normal variance without deviating from the plan is itself part of risk management, not a separate soft-skills topic.

Fixed-fractional sizing + a hard max-loss guardrail — feed `max_loss_per_lot` from notebook 07/10's `max_profit_loss()` output for a real strategy."""),
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
        md("""## Why an order management layer exists

A strategy that talks to the broker's REST API directly is one retry away from a
duplicate fill. An **order management system (OMS)** sits between "the strategy
decided to buy" and "the broker accepted an order" as a boundary that owns retry
safety, idempotency, and the order's lifecycle — so the strategy code never has to
reason about network failures, partial responses, or "did that POST actually land."

**Order types** you'll route through this layer:

- **Market** — fill immediately at the best available price. Fast, but the fill
  price is not guaranteed, especially in a fast-moving or thin book.
- **Limit** — fill only at your price or better. Guarantees price, not execution —
  the order can sit unfilled if the market never reaches it.
- **Stop-loss (SL)** — becomes a limit order once a trigger price is touched. Used
  to cap downside without watching the screen.
- **Stop-loss market (SL-M)** — becomes a market order once triggered. Guarantees
  the exit happens, not the price it happens at.

**Order lifecycle** — every order moves through a small state machine:
`pending` (sent, not yet acknowledged) → `open`/`trigger pending` (accepted,
resting) → a terminal state: `filled`, `partially filled`, `rejected`, or
`cancelled`. A production OMS tracks which state an order is in and refuses to,
say, cancel an order that's already filled, or re-place one that's still pending
a broker acknowledgment — that's the idempotency guarantee: retrying a `place()`
call after a timeout should never risk two live orders for one intended trade."""),
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
        md("Notice `place()`, `modify()`, and `cancel()` each map to exactly one broker endpoint and one lifecycle transition — that 1:1 mapping is what makes the layer auditable. If an order's state ever looks wrong, you can trace it to the single call that caused the transition, instead of hunting through strategy logic that also happens to talk to a broker."),
    ]


def body_17_paper_trading():
    return [
        md("""## Why paper trade before risking capital

Paper trading replays a strategy's signal logic against historical or live prices
and records what *would* have happened — without ever sending an order. It's the
cheapest way to catch a broken signal, an off-by-one in your date handling, or a
crossover rule that fires far more often than you intended, before any of it costs
money.

It is not a substitute for live trading, though — a paper trading loop like the
one below is missing three things that matter:

- **Slippage.** A market order to buy 75 quantity of an option doesn't always fill
  at the last traded price you saw; on a paper trade it always does.
- **Fill uncertainty.** A limit order might never fill, or might partially fill,
  when the real order book is thin. The simulation above assumes every signal
  becomes a full fill at the recorded close.
- **Psychology.** Paper trades carry no consequence, so they can't validate
  whether *you* will actually follow the strategy's exits when real money and a
  live drawdown are involved.

Treat a clean paper-trading run as evidence the *logic* works, not as evidence the
*strategy* is profitable — those are different claims."""),
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
        md("""## Keep signal generation and order dispatch as separate steps

It's tempting to write one function that computes an indicator and immediately
places an order. Don't — collapsing "decide" and "act" into one step removes the
only place you can intercept a bad decision before it becomes a live position.

The pattern below is deliberately three stages:

1. **`check_signal()`** — pure decision logic. Given data, it returns an intent
   (`BUY` / `SELL` / `HOLD`) and nothing else. It never touches a broker.
2. **Risk checks** — sit between the signal and the order (position sizing from
   notebook 15, a max-loss guard, a check that you're not already in this
   position). This is where a signal gets rejected even though it fired.
3. **`dispatch()`** — the only place an order is actually sent, and only after
   the first two stages agree.

`DRY_RUN` exists so you can run the full pipeline against live or historical data
and watch what it *would* do, with zero chance of a live fill — this is how you
catch a signal that fires every single bar (usually a bug, not an edge) before it
reaches a broker. That failure mode — a rule that looks profitable in a backtest
because it's actually just fitting noise in the sample it was tuned on — is called
**overfitting**, and a pipeline with a dry-run stage is one of the cheapest
defenses against shipping it."""),
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
        md("""## The request path of a real algo-trading system

Every earlier notebook in this course covered one link in a chain. This capstone
runs the whole chain in one script, so the shape of a real system is visible end
to end:

1. **Static IP + SDK (00-01)** — a stable, whitelistable egress address, because
   most Indian broker APIs bind an app to a fixed IP.
2. **Broker auth (02-05)** — exchange credentials for a session that can read
   data and place orders.
3. **Options math (06-10)** — price a leg, know its Greeks, and choose a strategy
   template with a bounded, understood risk profile (an iron condor, here).
4. **Data + backtesting (11-14)** — decide what to trade using historical
   evidence, not a hunch.
5. **Risk sizing (15)** — turn "this strategy has a known max loss per lot" into
   "here is how many lots this account is allowed to hold."
6. **Execution (16-18)** — an OMS that owns the order lifecycle, and a
   signal→dispatch boundary that can reject a bad decision before it fires.

`run_once()` below chains steps 3, 5, and 6 for a single iron condor: it sizes
the position from the account's risk budget, builds the four legs, and either
dry-run logs or dispatches each leg's order.

**This is a skeleton, not a trading system you should run with real capital.**
Every notebook in this course used illustrative pricing, demo data, or dry-run
dispatch — none of it accounted for brokerage, slippage, margin requirements, or
what happens when an order partially fills mid-adjustment. Moving from this to
live capital is a separate project: it needs its own risk review, a kill switch,
monitoring for when the strategy's live behavior diverges from its backtest, and
capital you can afford to lose while you find out where the model is wrong."""),
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
        md(f"""## What this course covered

static IP (00) → SDK (01) → broker auth (02-05) → options pricing and Greeks
(06-07) → strategy templates (08-10) → live data (11-12) → backtesting (13-14) →
position sizing (15) → order management, paper trading, and a signal pipeline
(16-18) → this capstone (19). Each stage above is a real, separately-testable
component of a trading system — the discipline is in keeping them separate, not
in any one clever indicator or strategy.

Continue with the broker API and indicator learning path in notebooks 20-23:
comparing broker APIs, computing 50 indicators without a TA dependency, wiring
broker candles into that indicator engine, and generating de-duplicated,
risk-checked alerts.

Keep building at [{SITE}/tools/strategy-builder]({SITE}/tools/strategy-builder), or grab your own static IP at [{SITE}/register]({SITE}/register)."""),
    ]


def body_20_broker_api_landscape():
    return [
        md("""## Scope and how to read the list

This is a **reviewed catalog of Indian retail brokers with public, first-party API documentation**, checked 12 August 2026. It is not a claim that every SEBI-registered broker exposes a retail API. “ServLoci route” means a maintained broker allowlist exists today; “adapter” means the same OHLCV/indicator pattern works, but the broker origin still needs explicit ServLoci support before order traffic can be proxied.

Broker plans, rate limits, authentication and static-IP rules change. Recheck the linked official source before production use. Never send broker passwords, PINs, TOTP seeds or access tokens to ServLoci."""),
        md("""## Public broker API inventory

| Broker / API | What the official API exposes | Typical auth | Official source | ServLoci route |
|---|---|---|---|---|
| Zerodha Kite Connect | Orders, portfolio, WebSocket quotes, paid historical data | OAuth-like daily request/access token | [Kite Connect](https://zerodha.com/products/api/) | Maintained (`kite`) |
| Upstox Developer API | Orders, portfolio, market data, sandbox, WebSockets | OAuth 2.0 | [Upstox docs](https://upstox.com/developer/api-documentation) | Maintained (`upstox`) |
| DhanHQ v2 | Orders, portfolio, quotes, historical data, live feed | Client ID + access token | [DhanHQ docs](https://dhanhq.co/docs/v2/) | Maintained (`dhan`) |
| FYERS API v3 | Orders, history, data socket and order socket | App ID + OAuth access token | [FYERS support](https://support.fyers.in/portal/en/kb/fyers-api-integrations) | Maintained (`fyers`) |
| Groww Trading API | Order and market-data APIs with Python/cURL docs | API key/access token flow | [Groww docs](https://groww.in/trade-api/docs) | Maintained (`groww`) |
| ICICI Direct Breeze | Orders, portfolio, historical data and streaming | API key + secret + session | [Breeze docs](https://api.icicidirect.com/breezeapi/documents/index.html) | Maintained (`icicidirect`) |
| Kotak Neo API v2 | Orders, portfolio and quotes via official SDK | Consumer key + TOTP/MPIN session | [Kotak Neo SDK](https://github.com/Kotak-Neo/Kotak-neo-api-v2) | Maintained (`kotak`, SOCKS5) |
| Angel One SmartAPI | Orders, portfolio, quotes, WebSocket and postbacks | API key + client login/TOTP tokens | [SmartAPI docs](https://smartapi.angelone.in/docs) | Adapter; route not yet maintained |
| Alice Blue ANT | Trading, portfolio and market-data APIs | App/client session | [ANT docs](https://ant.aliceblueonline.com/productdocumentation/) | Adapter; route not yet maintained |
| 5paisa Xstream | Order management, portfolio and market-data APIs | App credentials + client session | [Xstream docs](https://xstream.5paisa.com/dev-docs/) | Adapter; route not yet maintained |
| Shoonya / Finvasia | Orders, GTT, portfolio, REST/WebSocket market data | Vendor/app key + user session | [Shoonya docs](https://shoonya.com/api-documentation) | Adapter; route not yet maintained |
| Flattrade Pi | Orders, GTT/OCO, portfolio, WebSocket, postbacks | API key/secret + access token | [Pi v2 docs](https://pi.flattrade.in/docs) | Adapter; route not yet maintained |
| SAMCO Trade API v3.2 | Orders, portfolio, market data and WebSocket | OAuth 2.1 or direct session token | [SAMCO docs](https://docs-tradeapi.samco.in/) | Adapter; route not yet maintained |
| Tradejini API v2 | Orders, chart data, portfolio and WebSockets | OAuth/app access token | [Tradejini docs](https://developer.tradejini.com/docs) | Adapter; route not yet maintained |
| Motilal Oswal Trading API | Orders, reports, market and historical data | Client/app authentication | [MO API docs](https://invest.motilaloswal.com/moAPI/APIDocumentation/Introduction) | Adapter; route not yet maintained |
| Sharekhan Trading API | Orders, portfolio and market data | App/OAuth session | [Sharekhan docs](https://www.sharekhan.com/trading-api/documentation) | Adapter; route not yet maintained |
| Mastertrust REST API | Orders, portfolio, historical/live data, WebSocket | OAuth 2.0 | [Mastertrust docs](https://tradeapi.mastertrust.co.in/) | Adapter; route not yet maintained |
| Nuvama API Connect | Orders, portfolio, REST data and streaming | OAuth/app session | [Nuvama API Connect](https://www.nuvamawealth.com/api-connect/) | Adapter; route not yet maintained |

“Free API” can still exclude exchange-licensed real-time data, historical depth, account charges, brokerage, cloud egress or an external static IPv4. Compare the exact endpoint and plan you need—not the headline price."""),
        md("""## Selection checklist

1. Confirm the instruments and exchange segments you trade.
2. Confirm candle intervals, history depth, corporate-action handling and live-feed entitlement.
3. Check documented order limits, reconnect behavior, idempotency support, sandbox/paper support and postbacks.
4. Verify current static-IP and OAuth/2FA policy. From 1 April 2026, Indian retail-algo implementation rules materially affect client-direct API order traffic.
5. Test rejection, timeout, partial-fill and duplicate-order recovery before measuring latency.
6. Keep analysis/data reads direct. Route only the broker calls that must originate from the approved static address.

Start with a read-only profile or funds endpoint, then paper/dry-run, then the smallest permitted live order. An API feature table is not a reliability ranking or a recommendation to trade."""),
    ]


def body_21_top_50_indicators():
    return [
        md("""## The top 50 used in this course

- **Trend (1–11):** SMA, EMA, WMA, HMA, DEMA, TEMA, VWMA, MACD, MACD signal, PPO, TRIX.
- **Momentum (12–24):** ROC, Momentum, RSI, Stochastic %K/%D, Williams %R, CCI, Ultimate Oscillator, Awesome Oscillator, KST, TSI, Connors RSI, CMO.
- **Volatility/channels (25–36):** Bollinger upper/lower/bandwidth, ATR, NATR, True Range, Keltner upper/lower, Donchian upper/lower, standard deviation, historical volatility.
- **Directional/trend state (37–46):** ADX, +DI, −DI, Aroon up/down, Vortex +/−, Parabolic SAR, Ichimoku conversion/base.
- **Volume/money flow (47–50):** OBV, MFI, CMF, Accumulation/Distribution.

These are features, not buy/sell advice. Parameters are conventional teaching defaults and must be frozen before a fair backtest."""),
        code("!pip install -q pandas numpy matplotlib ipywidgets\n" + INDICATOR_ENGINE_SRC),
        md("""## Pick a stock and fetch real OHLCV

A seeded random walk can prove the engine returns 50 columns. It cannot show how RSI, MACD or Bollinger bands sit on a name that actually traded.

`yfinance` pulls public daily bars — no broker account, no API key. Yahoo ticker rules:

- NSE: `RELIANCE.NS`, `TCS.NS`  ·  BSE: `RELIANCE.BO`
- US: `AAPL`, `MSFT`  ·  indices: `^NSEI`, `^NSEBANK`, `^BSESN`, `^GSPC`

Use the stock selector in the next cell. Type any Yahoo symbol in **Custom** to override the list. Some indices report no volume, so the four volume/money-flow columns will be empty or zero — that is a data property, not a bug in the engine.

Prices are **auto-adjusted** for splits and dividends so a corporate action does not look like a crash. Unadjusted broker candles belong in notebook 22."""),
        code("""from IPython.display import display  # provided by Colab/Jupyter; imported explicitly for portability
import matplotlib.pyplot as plt

STOCK_UNIVERSE = {
    "Nifty 50": "^NSEI",
    "Bank Nifty": "^NSEBANK",
    "Sensex": "^BSESN",
    "Reliance": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Infosys": "INFY.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "SBI": "SBIN.NS",
    "ITC": "ITC.NS",
    "Larsen & Toubro": "LT.NS",
    "Hindustan Unilever": "HINDUNILVR.NS",
    "Bajaj Finance": "BAJFINANCE.NS",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "NVIDIA": "NVDA",
    "S&P 500": "^GSPC",
}

def load_ohlcv(ticker, period="2y"):
    # Daily OHLCV from Yahoo, already split/dividend adjusted.
    raw = yf.download(
        ticker, period=period, interval="1d",
        auto_adjust=True, progress=False, multi_level_index=False,
    )
    if raw is None or raw.empty:
        raise ValueError(f"yfinance returned no rows for {ticker!r} — check the Yahoo symbol.")
    bars = raw.rename(columns={c: str(c).lower() for c in raw.columns})
    needed = ["open", "high", "low", "close", "volume"]
    missing = [c for c in needed if c not in bars.columns]
    if missing:
        raise ValueError(f"{ticker}: download missing {missing}. Got {list(bars.columns)}")
    bars = bars[needed].apply(pd.to_numeric, errors="coerce").dropna(how="any")
    if len(bars) < 80:
        raise ValueError(
            f"{ticker}: only {len(bars)} bars — need ~80+ so long-window indicators can warm up."
        )
    return bars

def plot_families(ticker, bars, indicators):
    close = bars["close"]
    fig, axes = plt.subplots(
        4, 1, figsize=(11, 10), sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1, 1, 1]},
    )
    ax = axes[0]
    ax.plot(close.index, close, color="#1a1a1a", lw=1.1, label="Close")
    ax.plot(indicators.index, indicators["01_sma_20"], color="#2563eb", lw=1, label="SMA 20")
    ax.plot(indicators.index, indicators["02_ema_20"], color="#7c3aed", lw=1, label="EMA 20")
    ax.fill_between(
        indicators.index, indicators["26_bollinger_lower"], indicators["25_bollinger_upper"],
        color="#2563eb", alpha=0.08, label="Bollinger",
    )
    ax.set_title(f"{ticker} — price, trend and channels")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.grid(True, alpha=0.25)

    axes[1].plot(indicators.index, indicators["14_rsi_14"], color="#0f766e", lw=1)
    axes[1].axhline(70, color="#b45309", ls="--", lw=0.8)
    axes[1].axhline(30, color="#b45309", ls="--", lw=0.8)
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("RSI 14")
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(indicators.index, indicators["08_macd"], color="#1d4ed8", lw=1, label="MACD")
    axes[2].plot(indicators.index, indicators["09_macd_signal"], color="#be123c", lw=1, label="Signal")
    axes[2].axhline(0, color="#999", lw=0.6)
    axes[2].set_ylabel("MACD")
    axes[2].legend(loc="upper left", fontsize=8, frameon=False)
    axes[2].grid(True, alpha=0.25)

    axes[3].plot(indicators.index, indicators["37_adx_14"], color="#334155", lw=1, label="ADX")
    axes[3].plot(indicators.index, indicators["38_plus_di"], color="#15803d", lw=0.9, label="+DI")
    axes[3].plot(indicators.index, indicators["39_minus_di"], color="#b91c1c", lw=0.9, label="-DI")
    axes[3].axhline(25, color="#999", ls="--", lw=0.8)
    axes[3].set_ylabel("ADX / DI")
    axes[3].legend(loc="upper left", fontsize=8, frameon=False)
    axes[3].grid(True, alpha=0.25)
    fig.tight_layout()
    plt.show()

def run_indicators(ticker, period="2y", plot=True):
    bars = load_ohlcv(ticker, period)
    indicators = compute_top_50(bars)
    print(f"{ticker}: {len(bars)} daily bars, {bars.index.min().date()} -> {bars.index.max().date()}")
    if float(bars["volume"].fillna(0).sum()) == 0:
        print("Note: this symbol reports no volume (common on some indices). "
              "Volume indicators will be empty or zero.")
    print("indicator count:", indicators.shape[1])
    display(indicators.tail(5).T)
    assert indicators.shape[1] == 50
    if plot:
        plot_families(ticker, bars, indicators)
    return bars, indicators

# Seeded smoke test: the engine must always emit exactly 50 named columns,
# independent of whatever live ticker is selected next.
rng = np.random.default_rng(7)
n = 160
close = pd.Series(22000 + rng.normal(0, 70, n).cumsum())
demo = pd.DataFrame({
    "open": close.shift(1).fillna(close.iloc[0]),
    "high": close + rng.uniform(10, 90, n),
    "low": close - rng.uniform(10, 90, n),
    "close": close,
    "volume": rng.integers(100_000, 900_000, n),
}, index=pd.date_range("2025-01-01", periods=n, freq="B"))
assert compute_top_50(demo).shape[1] == 50
print("engine smoke test passed (50 columns on seeded OHLCV)")
"""),
        md("## Stock selector — run all 50 on the name you pick"),
        code("""# Stock selector. Use the dropdown, or type any Yahoo ticker in Custom.
# If widgets are unavailable (plain script), set TICKER / PERIOD and re-run.

TICKER = "RELIANCE.NS"   # default, and the fallback when widgets are missing
PERIOD = "2y"            # 6mo, 1y, 2y, 5y

try:
    import ipywidgets as W
    from ipywidgets import interactive_output
    _WIDGETS = True
except ImportError:
    _WIDGETS = False

if _WIDGETS:
    stock = W.Dropdown(options=list(STOCK_UNIVERSE.items()), value=TICKER, description="Stock:")
    custom = W.Text(value="", placeholder="e.g. INFY.NS or AAPL", description="Custom:")
    period = W.ToggleButtons(options=["6mo", "1y", "2y", "5y"], value=PERIOD, description="Lookback:")

    def _on_change(stock, custom, period):
        ticker = (custom or "").strip() or stock
        global TICKER, PERIOD, bars, indicators
        TICKER, PERIOD = ticker, period
        bars, indicators = run_indicators(ticker, period)

    ui = W.VBox([W.HBox([stock, period]), custom])
    out = interactive_output(_on_change, {"stock": stock, "custom": custom, "period": period})
    display(ui, out)
else:
    print("ipywidgets not installed — using TICKER / PERIOD. pip install ipywidgets for the dropdown.")
    bars, indicators = run_indicators(TICKER, PERIOD)
"""),
        md("""## What happens when an indicator "fires"

A textbook label is a description of the *last closed bar*, not a forecast. The cells below do three things for the ticker you just selected:

1. State the conventional reading (what a chartist would say).
2. Say whether that condition is true **on the latest bar**.
3. Measure what actually happened on *this* ticker over the next 10 sessions after past events.

That last step is the point. "RSI oversold" is a story; "RSI crossed below 30, then the next 10 days averaged X% on this name" is a fact about one sample path. Notebook 27 tests a few of these claims more carefully; notebook 33 shows why turning them into a price forecast is usually a leaky demo."""),
        code("""def ensure_selected():
    # Re-run the selector cell first if you changed the ticker. This only
    # fetches if a later cell is executed in isolation.
    global TICKER, PERIOD, bars, indicators
    if "bars" not in globals() or "indicators" not in globals():
        TICKER = globals().get("TICKER", "RELIANCE.NS")
        PERIOD = globals().get("PERIOD", "2y")
        bars, indicators = run_indicators(TICKER, PERIOD, plot=False)
    return bars, indicators

def scenario_flags(bars, indicators):
    close = bars["close"]
    sma, ema = indicators["01_sma_20"], indicators["02_ema_20"]
    macd, sig = indicators["08_macd"], indicators["09_macd_signal"]
    rsi = indicators["14_rsi_14"]
    stoch, wr = indicators["15_stochastic_k"], indicators["17_williams_r"]
    upper, lower = indicators["25_bollinger_upper"], indicators["26_bollinger_lower"]
    bw, atr = indicators["27_bollinger_bandwidth"], indicators["28_atr_14"]
    adx = indicators["37_adx_14"]
    pdi, mdi = indicators["38_plus_di"], indicators["39_minus_di"]
    obv, mfi = indicators["47_obv"], indicators["48_mfi_14"]
    flags = pd.DataFrame(index=bars.index)
    flags["price_cross_above_sma20"] = (close.shift(1) <= sma.shift(1)) & (close > sma)
    flags["price_cross_below_sma20"] = (close.shift(1) >= sma.shift(1)) & (close < sma)
    flags["ema_above_sma"] = ema > sma
    flags["macd_bullish_cross"] = (macd.shift(1) <= sig.shift(1)) & (macd > sig)
    flags["macd_bearish_cross"] = (macd.shift(1) >= sig.shift(1)) & (macd < sig)
    flags["rsi_enters_oversold"] = (rsi.shift(1) >= 30) & (rsi < 30)
    flags["rsi_enters_overbought"] = (rsi.shift(1) <= 70) & (rsi > 70)
    flags["rsi_oversold_now"] = rsi < 30
    flags["rsi_overbought_now"] = rsi > 70
    flags["stoch_enters_oversold"] = (stoch.shift(1) >= 20) & (stoch < 20)
    flags["williams_enters_oversold"] = (wr.shift(1) >= -80) & (wr < -80)
    def rising_edge(s):
        cur = s.fillna(False).astype(bool)
        prev = s.shift(1).fillna(False).astype(bool)
        return cur & ~prev

    flags["bollinger_squeeze"] = bw < bw.rolling(60, min_periods=40).quantile(0.2)
    flags["squeeze_starts"] = rising_edge(flags["bollinger_squeeze"])
    flags["close_above_upper_band"] = close > upper
    flags["walks_upper_band"] = rising_edge(flags["close_above_upper_band"])
    flags["close_below_lower_band"] = close < lower
    flags["walks_lower_band"] = rising_edge(flags["close_below_lower_band"])
    flags["atr_expanding"] = atr > atr.rolling(20, min_periods=10).mean() * 1.3
    flags["atr_expansion_starts"] = rising_edge(flags["atr_expanding"])
    flags["adx_trend_turns_on"] = (adx.shift(1) <= 25) & (adx > 25)
    flags["adx_uptrend"] = (adx > 25) & (pdi > mdi)
    flags["adx_downtrend"] = (adx > 25) & (mdi > pdi)
    flags["adx_chop"] = adx < 20
    flags["obv_bearish_div"] = (close >= close.rolling(20, min_periods=10).max()) & (
        obv < obv.rolling(20, min_periods=10).max()
    )
    flags["obv_div_starts"] = rising_edge(flags["obv_bearish_div"])
    flags["mfi_enters_oversold"] = (mfi.shift(1) >= 20) & (mfi < 20)
    return flags.fillna(False)

def event_aftermath(bars, flags, name, horizon=10):
    close = bars["close"]
    fwd = close.shift(-horizon) / close - 1
    hits = flags[name].astype(bool)
    sample = fwd[hits].dropna()
    last = flags.index[hits][-1].date() if hits.any() else None
    return {
        "scenario": name,
        "events": int(hits.sum()),
        f"mean_{horizon}d": None if sample.empty else float(sample.mean()),
        f"up_rate_{horizon}d": None if sample.empty else float((sample > 0).mean()),
        "last_date": last,
    }

def report_scenario(title, story, names, now_keys=None):
    b, ind = ensure_selected()
    flags = scenario_flags(b, ind)
    latest = flags.iloc[-1]
    print(f"{TICKER}  last bar {b.index[-1].date()}  close {float(b['close'].iloc[-1]):.2f}")
    print(title)
    print(story)
    print()
    if now_keys:
        for key in now_keys:
            print(f"  now  {key:28s}  {bool(latest[key])}")
    print()
    rows = [event_aftermath(b, flags, name) for name in names]
    table = pd.DataFrame(rows)
    display(table)
    recent = flags[names].tail(8)
    recent.index = recent.index.date
    print("recent flags (last 8 sessions):")
    display(recent)
    return flags

bars, indicators = ensure_selected()
flags = scenario_flags(bars, indicators)
print(f"scenario columns: {list(flags.columns)}")
print(f"{TICKER}: {int(flags.any(axis=1).sum())} sessions had at least one flag")
"""),
        md("""### Latest snapshot — which stories are true *today*

Run this after the selector. True means the condition holds on the **last closed** session, so any action belongs on the *next* tradable bar (notebook 29)."""),
        code("""b, ind = ensure_selected()
flags = scenario_flags(b, ind)
last = flags.iloc[-1]
close = float(b["close"].iloc[-1])
row = {
    "close": close,
    "sma20": float(ind["01_sma_20"].iloc[-1]),
    "ema20": float(ind["02_ema_20"].iloc[-1]),
    "rsi14": float(ind["14_rsi_14"].iloc[-1]),
    "macd": float(ind["08_macd"].iloc[-1]),
    "macd_signal": float(ind["09_macd_signal"].iloc[-1]),
    "bb_bandwidth": float(ind["27_bollinger_bandwidth"].iloc[-1]),
    "atr14": float(ind["28_atr_14"].iloc[-1]),
    "adx14": float(ind["37_adx_14"].iloc[-1]),
    "+DI": float(ind["38_plus_di"].iloc[-1]),
    "-DI": float(ind["39_minus_di"].iloc[-1]),
    "mfi14": float(ind["48_mfi_14"].iloc[-1]),
}
print(f"{TICKER} snapshot @ {b.index[-1].date()}")
display(pd.Series(row).to_frame("value"))
live = last[["ema_above_sma", "rsi_oversold_now", "rsi_overbought_now",
             "close_above_upper_band", "close_below_lower_band",
             "bollinger_squeeze", "atr_expanding",
             "adx_uptrend", "adx_downtrend", "adx_chop", "obv_bearish_div"]]
print("live conditions on the last closed bar:")
display(live.to_frame("true"))
firing = [name for name, on in live.items() if bool(on)]
print("firing now:", firing or "(none of the live-state flags)")
"""),
        md("""### Child: trend — SMA/EMA and MACD

**Textbook.** Price crossing back above the 20-day SMA is a short-term "reclaim." EMA sitting above SMA is a rising-average regime. MACD crossing above its signal line is the classic *possible* shift in short-term trend direction.

**What actually happens.** MACD is a lagging confirmation, not a prediction. A reclaim in a falling market often fails. The table is this ticker's own 10-session aftermath — not a license to buy the cross."""),
        code("""report_scenario(
    "TREND",
    "Reclaim / lose the 20-day average, and MACD crossing its signal.",
    names=["price_cross_above_sma20", "price_cross_below_sma20",
           "macd_bullish_cross", "macd_bearish_cross"],
    now_keys=["ema_above_sma"],
)
"""),
        md("""### Child: momentum — RSI, Stochastic, Williams %R

**Textbook.** RSI below 30 (or Stochastic below 20, Williams below −80) is "oversold": price has fallen far and fast relative to its recent range. Above 70 / 80 is "overbought."

**What actually happens.** In a strong uptrend RSI can sit above 70 for weeks while price keeps climbing. Oversold is a *stretched* reading, not a scheduled bounce. If the 10-day up-rate after `rsi_enters_oversold` is near a coin flip on this name, the folklore is not earning its keep here."""),
        code("""report_scenario(
    "MOMENTUM",
    "Oscillators entering stretched zones. Entry = first bar that crosses the threshold.",
    names=["rsi_enters_oversold", "rsi_enters_overbought",
           "stoch_enters_oversold", "williams_enters_oversold"],
    now_keys=["rsi_oversold_now", "rsi_overbought_now"],
)
"""),
        md("""### Child: volatility — Bollinger squeeze, band walks, ATR expansion

**Textbook.** A Bollinger squeeze (bandwidth in the lowest 20% of the last 60 sessions) says range has compressed and a larger move often follows — **direction unknown**. Close above the upper band is a "walk"; close below the lower band is a stretch the other way. ATR expanding means the typical daily range just jumped.

**What actually happens.** Squeezes precede both breakouts and fakeouts. Walking the upper band in a trend is continuation more often than reversal. ATR expansion is a *size* signal (widen stops, cut size), not an entry."""),
        code("""report_scenario(
    "VOLATILITY",
    "Compressed range, band extremes, and a jump in typical true range.",
    names=["squeeze_starts", "walks_upper_band",
           "walks_lower_band", "atr_expansion_starts"],
    now_keys=["bollinger_squeeze", "close_above_upper_band",
              "close_below_lower_band", "atr_expanding"],
)
"""),
        md("""### Child: directional state — ADX, +DI, −DI

**Textbook.** ADX above ~25: the market is trending, not chopping. +DI above −DI is the direction; ADX is only the strength gauge. ADX crossing up through 25 is "a trend is turning on." ADX below 20 is chop — trend-following setups usually bleed.

**What actually happens.** ADX says nothing about which way, and a newly "on" trend can be the last third of the move. Use it as a *filter* on a trend idea, not as a standalone long/short."""),
        code("""report_scenario(
    "DIRECTIONAL",
    "Trend on/off and which side is in control.",
    names=["adx_trend_turns_on"],
    now_keys=["adx_uptrend", "adx_downtrend", "adx_chop"],
)
print()
print(f"ADX now {float(indicators['37_adx_14'].iloc[-1]):.1f}  "
      f"+DI {float(indicators['38_plus_di'].iloc[-1]):.1f}  "
      f"-DI {float(indicators['39_minus_di'].iloc[-1]):.1f}")
"""),
        md("""### Child: volume — OBV divergence and MFI

**Textbook.** Price making a 20-day high while OBV is not is a bearish divergence: fewer participants are backing the high. MFI below 20 is an RSI-like stretch that includes volume.

**What actually happens.** On indices with empty volume these flags are meaningless. Even with real volume, a single 20-day divergence is a warning to treat trend/momentum reads more skeptically — not a sell ticket. Skip this cell's conclusion if the volume sum printed above was zero."""),
        code("""report_scenario(
    "VOLUME",
    "Price high without OBV confirmation, and MFI entering oversold.",
    names=["obv_div_starts", "mfi_enters_oversold"],
    now_keys=["obv_bearish_div"],
)
"""),
        md("""### Child: aftermath board — every event, one table

One ticker, one window, overlapping 10-day forward returns. This is a *research question* ("did this condition tend to precede that outcome"), not a backtest you can trade. Overlapping windows overstate how much independent evidence you have — see notebook 27 and 29."""),
        code("""b, ind = ensure_selected()
flags = scenario_flags(b, ind)
event_names = [
    "price_cross_above_sma20", "price_cross_below_sma20",
    "macd_bullish_cross", "macd_bearish_cross",
    "rsi_enters_oversold", "rsi_enters_overbought",
    "stoch_enters_oversold", "williams_enters_oversold",
    "squeeze_starts", "walks_upper_band", "walks_lower_band",
    "atr_expansion_starts", "adx_trend_turns_on",
    "obv_div_starts", "mfi_enters_oversold",
]
board = pd.DataFrame([event_aftermath(b, flags, name) for name in event_names])
board = board.sort_values("events", ascending=False)
print(f"{TICKER}  10-session aftermath after each event type")
display(board)

# Mark the four most common event types on price so you can see clustering.
top = board["scenario"].head(4).tolist()
fig, ax = plt.subplots(figsize=(11, 3.6))
ax.plot(b.index, b["close"], color="#1a1a1a", lw=1.0, label="Close")
colors = ["#2563eb", "#be123c", "#0f766e", "#7c3aed"]
for name, color in zip(top, colors):
    hits = b.index[flags[name].astype(bool)]
    ax.scatter(hits, b.loc[hits, "close"], s=18, color=color, label=name, zorder=3)
ax.set_title(f"{TICKER} — most frequent scenario dates")
ax.legend(loc="upper left", fontsize=7, frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
plt.show()
"""),
        md("""## Reading each family

A number alone is not a signal — read each family for what it actually measures, not what you want it to say.

- **Trend (SMA/EMA/MACD):** where price has been, smoothed. A rising EMA doesn't predict the next bar; it describes the recent path. Classic read: MACD crossing above its signal line marks a *possible* shift in short-term trend direction — it lags, so it confirms more often than it predicts.
- **Momentum (RSI/Stochastic/Williams %R):** how fast and how far price has moved relative to its own recent range. Textbook thresholds — RSI above 70 "overbought", below 30 "oversold" — describe stretched conditions, not reversal timing. In a strong trend, RSI can sit above 70 for weeks while price keeps climbing.
- **Volatility (Bollinger/ATR/Keltner):** how much price is moving, not which direction. A Bollinger "squeeze" (bands narrowing) flags compressed volatility that often precedes a bigger move — in either direction. ATR is mainly used to size stops and positions to current volatility, not to time entries.
- **Directional state (ADX/+DI/−DI):** ADX above roughly 25 is a conventional cutoff for "the market is trending, not chopping" — it says nothing about which way. +DI above −DI is the direction; ADX is the strength gauge.
- **Volume (OBV/MFI/CMF):** whether volume is confirming or contradicting the price move. Price rising while OBV falls (bearish divergence) means fewer participants are backing the rally — a warning to weigh trend/momentum reads more skeptically, not a stand-alone sell signal.

None of these families is reliable in isolation. Every real system in this course combines at least a trend/momentum read with a volatility or directional filter before treating anything as a signal — see notebook 23.

**Next in this school:** [correlation across a basket](32_stock_correlation_and_pairs.ipynb), [prediction baselines that have to beat naive](33_return_prediction_baselines.ipynb), [portfolio weights, frontier and drawdown](34_portfolio_analytics.ipynb)."""),
        md("""## Avoid the three common research errors

- **Warm-up leakage:** keep early `NaN` values; do not backfill an indicator with future information.
- **Same-bar fills:** a signal using a candle close can normally act only on the next tradable event in a bar-based backtest.
- **Unadjusted data:** splits, bonuses, symbol changes and futures rolls can create fake signals. Use broker/exchange metadata and document adjustments.

For production, compare a sample against a second implementation. Small differences can come from Wilder versus EMA smoothing, population versus sample deviation, and candle/session boundaries."""),
    ]


def body_22_broker_indicator_pipeline():
    return [
        md("""## One normalized shape for every broker

Broker payloads differ, but indicators need only `timestamp, open, high, low, close, volume`. Keep a small fetch adapter per broker, normalize immediately, and make the rest of the research code broker-neutral. Market-data reads stay direct; create the ServLoci-routed SDK client only at the order boundary."""),
        md("""## Why normalize, and why separate reads from writes

Every broker in notebook 20 names and shapes candles differently: some return `date`, others `timestamp` or `time`; some report volume as a string; timestamps arrive in UTC, IST, or with no timezone at all; a few brokers roll futures/index candles at a different session boundary than others. If `compute_top_50()` (or any indicator engine) has to know about each broker's quirks, every new broker doubles the surface area for a silent bug — a swapped high/low column produces indicators that run without error and are simply wrong.

`normalize_ohlcv()` is the one place that translation happens. Everything downstream — indicators, backtests, alerts — only ever sees the same five columns, so a broker swap or a new adapter never touches research code.

The read/write split matters for a different reason: market-data reads (candles, quotes) are high-volume, idempotent, and low-risk if they fail. Order writes are low-volume, side-effecting, and expensive if they fail wrong. Routing both through the same static IP is fine — collapsing them into the same code path is not. Keep the fetch adapters here free of any broker session that's also authorized to place orders; construct the order-capable client only at the boundary in notebook 16."""),
        code("!pip install -q pandas numpy requests\n" + INDICATOR_ENGINE_SRC),
        code("""from IPython.display import display  # provided by Colab/Jupyter; imported explicitly for portability

def normalize_ohlcv(records, mapping):
    raw = pd.DataFrame(records).rename(columns={source: target for target, source in mapping.items()})
    needed = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = set(needed).difference(raw.columns)
    if missing:
        raise ValueError(f"adapter did not provide: {sorted(missing)}")
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
    bars = raw.set_index("timestamp")[["open", "high", "low", "close", "volume"]].sort_index()
    return bars.apply(pd.to_numeric, errors="raise")

# Generic example: replace this callback with a broker SDK/API fetch.
def demo_fetch():
    rng = np.random.default_rng(12); n = 320
    close = pd.Series(24000 + rng.normal(0, 60, n).cumsum())
    return pd.DataFrame({
        "time": pd.date_range("2025-01-01", periods=n, freq="B", tz="Asia/Kolkata"),
        "o": close.shift(1).fillna(close.iloc[0]), "h": close + 50,
        "l": close - 50, "c": close, "v": rng.integers(100000, 800000, n),
    }).to_dict("records")

bars = normalize_ohlcv(demo_fetch(), {
    "timestamp": "time", "open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"
})
features = compute_top_50(bars)
dataset = bars.join(features)
display(dataset.tail(3))
"""),
        md("## Concrete broker fetch adapters"),
        code("""# Zerodha Kite (direct read; create `kite` with its normal authenticated flow)
def fetch_kite_daily(kite, instrument_token, start, end):
    rows = kite.historical_data(instrument_token, start, end, "day", continuous=False, oi=False)
    return normalize_ohlcv(rows, {
        "timestamp": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"
    })

# FYERS v3 (direct read; `fyers.history` returns candles as [epoch,o,h,l,c,v])
def fetch_fyers_daily(fyers, symbol, start_epoch, end_epoch):
    response = fyers.history(data={"symbol": symbol, "resolution": "D", "date_format": "0",
                                   "range_from": str(start_epoch), "range_to": str(end_epoch), "cont_flag": "1"})
    rows = [dict(zip(["timestamp", "open", "high", "low", "close", "volume"], row))
            for row in response.get("candles", [])]
    return normalize_ohlcv(rows, {name: name for name in rows[0]} if rows else {
        "timestamp": "timestamp", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"
    })

# DhanHQ v2 REST (direct read). Security ID and segment come from Dhan's instrument master.
def fetch_dhan_daily(client_id, access_token, security_id, from_date, to_date):
    import requests
    response = requests.post("https://api.dhan.co/v2/charts/historical", headers={
        "access-token": access_token, "client-id": client_id, "Content-Type": "application/json"
    }, json={"securityId": str(security_id), "exchangeSegment": "IDX_I", "instrument": "INDEX",
             "expiryCode": 0, "oi": False, "fromDate": from_date, "toDate": to_date}, timeout=30)
    response.raise_for_status(); payload = response.json()
    rows = [dict(zip(["timestamp", "open", "high", "low", "close", "volume"], values))
            for values in zip(payload["timestamp"], payload["open"], payload["high"], payload["low"], payload["close"], payload["volume"])]
    return normalize_ohlcv(rows, {k: k for k in ("timestamp", "open", "high", "low", "close", "volume")})
"""),
        md("""For Upstox, Groww, Breeze, Kotak Neo and every broker in notebook 20, implement only the fetch callback using that broker’s current SDK, then pass its records through `normalize_ohlcv()` and `compute_top_50()`. Keeping this boundary small makes schema changes visible and testable.

Cache raw candles with broker, symbol, interval, timezone, fetch time and adjustment policy. Do not silently mix feeds: two vendors can close the same candle differently because of session and timestamp rules."""),
    ]


def body_23_alerts_and_servloci():
    return [
        md("""## Alert first, order later

This notebook turns completed candles into stateful alerts. It de-duplicates repeated signals, includes the observed values, and defaults to console output. Telegram and generic webhook sinks are opt-in. A separate, dry-run order boundary shows where ServLoci belongs."""),
        md("""## Why de-duplicate, and why cool down

A signal like "MACD crossed up" is a property of two adjacent candles, not a single instant. If the condition stays true for several bars in a row — or your polling loop checks more often than a new candle closes — a naive check fires the same alert repeatedly for what is, functionally, one event. `AlertRouter.should_send()` below keys each alert by symbol + condition + candle timestamp and enforces a cooldown, so re-checking the same closed candle, or a genuinely flat market, produces silence instead of spam. Silence on "no new signal" is the correct, boring outcome — treat repeated alerts for the same event as a bug, not confirmation."""),
        code("!pip install -q pandas numpy requests\n" + INDICATOR_ENGINE_SRC),
        code("""from dataclasses import dataclass
from datetime import datetime, timezone
import json, os, time, requests

@dataclass(frozen=True)
class Alert:
    key: str
    symbol: str
    side: str
    message: str
    observed_at: str

class AlertRouter:
    def __init__(self, cooldown_seconds=900):
        self.cooldown = cooldown_seconds
        self.sent_at = {}

    def should_send(self, alert):
        now = time.time(); previous = self.sent_at.get(alert.key, 0)
        if now - previous < self.cooldown:
            return False
        self.sent_at[alert.key] = now
        return True

    def console(self, alert):
        print(json.dumps(alert.__dict__, indent=2))

    def webhook(self, alert, url):
        response = requests.post(url, json={"text": alert.message, "alert": alert.__dict__}, timeout=10)
        response.raise_for_status()

    def telegram(self, alert, bot_token, chat_id):
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(url, json={"chat_id": chat_id, "text": alert.message}, timeout=10)
        response.raise_for_status()

def closed_candle_signal(symbol, bars, indicators):
    # Call only after the broker confirms the candle is closed.
    latest, previous = indicators.iloc[-1], indicators.iloc[-2]
    price = float(bars["close"].iloc[-1])
    crossed_up = previous["08_macd"] <= previous["09_macd_signal"] and latest["08_macd"] > latest["09_macd_signal"]
    risk_ok = 45 <= latest["14_rsi_14"] <= 70 and latest["37_adx_14"] >= 20
    if not (crossed_up and risk_ok):
        return None
    when = bars.index[-1].isoformat()
    return Alert(key=f"{symbol}:macd-up:{when}", symbol=symbol, side="BUY_WATCH",
                 message=f"{symbol}: MACD crossed up; close={price:.2f}, RSI={latest['14_rsi_14']:.1f}, ADX={latest['37_adx_14']:.1f}",
                 observed_at=when)
"""),
        code("""# Reproducible dry run. Replace `bars` with notebook 22's broker adapter output.
rng = np.random.default_rng(99); n = 340
close = pd.Series(20000 + np.r_[rng.normal(-3, 30, 300), rng.normal(25, 20, 40)].cumsum())
bars = pd.DataFrame({"open": close.shift().fillna(close.iloc[0]), "high": close+35,
                     "low": close-35, "close": close, "volume": rng.integers(100000, 900000, n)},
                    index=pd.date_range("2025-01-01", periods=n, freq="15min", tz="Asia/Kolkata"))
indicators = compute_top_50(bars)
alert = closed_candle_signal("NIFTY", bars, indicators)
router = AlertRouter()
if alert and router.should_send(alert):
    router.console(alert)
    if os.getenv("ALERT_WEBHOOK_URL"):
        router.webhook(alert, os.environ["ALERT_WEBHOOK_URL"])
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        router.telegram(alert, os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])
else:
    print("No new completed-candle alert. This is a valid outcome.")
"""),
        md("""## Optional ServLoci order boundary (dry-run by default)

An alert is a hypothesis someone should look at — it is not authorization to trade. Before any alert is allowed to become an order, a pre-dispatch risk gate should check, at minimum: is the requested quantity within a hard per-order cap, is the account already at its position limit for this symbol, is the market actually open, and has this exact alert (by its de-dup key) already been dispatched. `dispatch_after_risk_checks()` below enforces the quantity cap and defaults `DRY_RUN = True`, so flipping it off is a deliberate, single-line decision — not something that happens by omission."""),
        code("""DRY_RUN = True

def dispatch_after_risk_checks(alert, quantity, max_quantity=1):
    if alert is None: return None
    if quantity < 1 or quantity > max_quantity: raise ValueError("quantity rejected by local risk gate")
    intent = {"symbol": alert.symbol, "side": "BUY", "quantity": quantity,
              "client_order_id": alert.key, "signal_time": alert.observed_at}
    if DRY_RUN:
        print("DRY RUN — order intent not sent:", intent)
        return intent

    # Configure before constructing the supported broker SDK client:
    # from servloci import configure
    # configure(token=os.environ["STATIC_IP_TOKEN"], broker=os.environ["BROKER"])
    # broker = build_current_broker_client_from_private_secrets()
    # return broker.place_order(... current broker fields ...)
    raise RuntimeError("Wire one reviewed broker adapter before disabling DRY_RUN")

dispatch_after_risk_checks(alert, quantity=1)
"""),
        md("""Production alerts should persist de-duplication state outside the notebook, retry with bounded backoff, record delivery responses and expose a heartbeat/no-data alert. The order worker should independently re-check candle freshness, position, funds/margin, market session, maximum loss, quantity and the idempotency key. An alert is evidence to review—not proof of a profitable trade."""),
    ]


# ── Stock Market School (yfinance, no broker account needed) ──────────────
# Chapters 24-35. 24-34 use yfinance_setup_cells(); 35 adds Drive + Prophet.
# (see NOTEBOOKS entries below) — no ServLoci signup required to run these.

def body_24_reading_the_market():
    return [
        md("""## Start here — no account, no API key, no waiting

Every other notebook in this series eventually asks you to whitelist an IP or authenticate against a broker. This one doesn't, on purpose. `yfinance` reads Yahoo Finance's public end-of-day (and near-real-time delayed) data over plain HTTPS — no credentials, no approval process, no rate-limited sandbox. That makes it the right place to *actually learn what market data is* before you ever touch an order API.

**Ticker conventions.** Yahoo's symbol format is not the same everywhere:

- NSE-listed stocks take an `.NS` suffix — `RELIANCE.NS`, `TCS.NS`, `INFY.NS`.
- BSE-listed stocks take `.BO` instead.
- Indices are prefixed with `^` — `^NSEI` is Nifty 50, `^BSESN` is Sensex, `^GSPC` is the S&P 500.
- US stocks have no suffix at all — `AAPL`, `MSFT`.

Get this wrong (e.g. request `RELIANCE` instead of `RELIANCE.NS`) and yfinance either returns an empty frame or silently resolves to an unrelated ticker on another exchange — always check the row count and the first few rows before trusting a pull."""),
        code("""nse = yf.download(NSE_TICKER, period="1y", interval="1d", progress=False, multi_level_index=False)
us = yf.download(US_TICKER, period="1y", interval="1d", progress=False, multi_level_index=False)
index = yf.download(INDEX_TICKER, period="1y", interval="1d", progress=False, multi_level_index=False)

print(NSE_TICKER, "rows:", len(nse))
print(US_TICKER, "rows:", len(us))
print(INDEX_TICKER, "rows:", len(index))
nse.tail()
"""),
        md("""## What's actually in a row of OHLCV

Every row is one trading session: **O**pen, **H**igh, **L**ow, **C**lose, and **V**olume. Open and Close are auction prices (in India, set by the pre-open and closing call auctions); High and Low are the extremes touched intraday; Volume is shares traded, not rupee/dollar turnover.

A candlestick is just that same row drawn as a shape: a "body" spanning Open→Close (colored by whether the session closed up or down) and "wicks" reaching to the High and Low. Reading one candle tells you very little — reading a *sequence* of them is what technical analysis (notebook 27) is actually about.

**`Close` vs `Adj Close` — the bug that quietly wrecks backtests.** `Close` is the literal traded price that day. `Adj Close` retroactively adjusts every historical price for dividends and stock splits, so that a simple percentage-return calculation across the whole series stays correct. If a stock does a 1:2 split, its raw Close halves overnight — a backtest using raw Close would show a fake 50% crash on the split date. Always compute returns from `Adj Close`, never from `Close`, unless you have a specific reason not to (yfinance's newer default already auto-adjusts `Close` in some call modes — check the columns you actually got back rather than assuming)."""),
        code("""ticker = yf.Ticker(NSE_TICKER)

divs = ticker.dividends
splits = ticker.splits
print("Dividend events in history:", len(divs))
print(divs.tail())
print("\\nSplit events in history:", len(splits))
print(splits)

# Ticker().history() is the equivalent of yf.download() for a single symbol,
# and exposes the same adjustment behavior:
hist = ticker.history(period="6mo", auto_adjust=True)
hist[["Open", "High", "Low", "Close", "Volume"]].head()
"""),
        md("""## Settlement: why "the trade happened" isn't "the money moved"

A filled order is not the end of the transaction. India moved to **T+1 settlement** in 2023 — shares and funds change hands one business day after the trade date. The US settles most equities on **T+1** as well since mid-2024. This matters directly for algo trading: your buying power and holdings are not the same thing as "what I clicked buy on this morning," and any position-tracking code (see notebook 16's OMS) has to account for the settlement lag, not just the fill.

Next: notebook 25 turns these raw prices into the return and risk numbers every strategy claim should be judged by."""),
    ]


def body_25_returns_and_risk():
    return [
        md("""## The number that matters is never just "the return"

"This strategy returned 40%!" is not a complete sentence — over what period, with what volatility, and how far underwater did it go before that 40%? Free trading content routinely leads with a headline return and drops the other three numbers, because the other three are usually less flattering. This notebook computes all four, on real data, so you can see why they matter together.

**Simple vs log returns.** Simple return is `(P1 - P0) / P0` — intuitive, but simple returns don't add across time (a +50% day followed by a -50% day does not net to 0%). Log return, `ln(P1 / P0)`, does add across time and is what you should use for anything involving compounding, multi-period aggregation, or volatility math."""),
        code("""nse = yf.download(NSE_TICKER, period="2y", interval="1d", progress=False, auto_adjust=True, multi_level_index=False)
prices = nse["Close"]

simple_returns = prices.pct_change().dropna()
log_returns = np.log(prices / prices.shift(1)).dropna()

print("Simple return, first 3 days:\\n", simple_returns.head(3))
print("\\nLog return, first 3 days:\\n", log_returns.head(3))

# The gap between them widens with the size of the daily move — small moves,
# simple and log returns are almost identical; large moves, they diverge.
"""),
        md("""## Volatility: the risk you're actually taking to earn that return

Annualized volatility scales daily return standard deviation up by `sqrt(252)` (the approximate number of trading sessions in a year) — it's the standard way to compare "how bumpy was the ride" across strategies or instruments regardless of how much history you pulled."""),
        code("""daily_vol = log_returns.std()
annualized_vol = daily_vol * np.sqrt(252)
print(f"{NSE_TICKER} daily vol: {daily_vol:.4%}, annualized: {annualized_vol:.2%}")

# Compare against the index, over the SAME window — a stock more volatile
# than the index it belongs to is carrying idiosyncratic (stock-specific) risk
# on top of market risk.
idx = yf.download(INDEX_TICKER, period="2y", interval="1d", progress=False, auto_adjust=True, multi_level_index=False)
idx_log_returns = np.log(idx["Close"] / idx["Close"].shift(1)).dropna()
idx_annualized_vol = idx_log_returns.std() * np.sqrt(252)
print(f"{INDEX_TICKER} annualized vol: {idx_annualized_vol:.2%}")
"""),
        md("""## Sharpe, Sortino, and drawdown — the numbers that keep a headline return honest

- **Sharpe ratio** — excess return over the risk-free rate, divided by volatility. High return with low Sharpe means the return came with a rough ride; a strategy claim without a Sharpe number is an incomplete claim.
- **Sortino ratio** — the same idea, but only penalizes *downside* volatility. Two strategies with identical Sharpe can have very different Sortino if one strategy's volatility is mostly big up-days (which Sharpe punishes even though nobody minds them).
- **Max drawdown** — the largest peak-to-trough decline in the equity curve. This is the number that answers "could I have psychologically and financially survived holding through this strategy's worst stretch?" — and it's the number retail marketing omits most often."""),
        code("""RISK_FREE_RATE = 0.065  # approx. Indian 10Y G-Sec yield — swap for the current rate when you run this

excess_daily = log_returns - (RISK_FREE_RATE / 252)
sharpe = excess_daily.mean() / log_returns.std() * np.sqrt(252)

downside = log_returns[log_returns < 0]
sortino = excess_daily.mean() / downside.std() * np.sqrt(252)

cumulative = (1 + simple_returns).cumprod()
running_max = cumulative.cummax()
drawdown = (cumulative - running_max) / running_max
max_drawdown = drawdown.min()

print(f"Sharpe:      {sharpe:.2f}")
print(f"Sortino:     {sortino:.2f}")
print(f"Max drawdown: {max_drawdown:.2%}")
"""),
        md("""## The cherry-picking trap, demonstrated

Pull the *same* ticker over two different windows and compare the headline return. This is exactly how misleading "look at this return!" screenshots get made — not usually through outright fabrication, just through choosing a window that happens to start at a low and end at a high."""),
        code("""window_a = yf.download(NSE_TICKER, start="2020-03-23", end="2021-03-23", progress=False, auto_adjust=True, multi_level_index=False)
window_b = yf.download(NSE_TICKER, period="1y", progress=False, auto_adjust=True, multi_level_index=False)

return_a = window_a["Close"].iloc[-1] / window_a["Close"].iloc[0] - 1
return_b = window_b["Close"].iloc[-1] / window_b["Close"].iloc[0] - 1

print(f"Return from the 2020 crash low, 1 year forward: {return_a:.1%}")
print(f"Return over the most recent 1 year: {return_b:.1%}")
print("Same ticker. Same length of window. Very different number — the start date did all the work.")
"""),
        md("Next: notebook 26 puts the company itself under the microscope — fundamentals, not just price history."),
    ]


def body_26_fundamental_analysis():
    return [
        md("""## Price tells you what; filings tell you why

Most algo-trading courses skip fundamentals entirely — they jump straight to candles and indicators, as if a ticker were just a stream of numbers with no company behind it. Most stock-market-literacy courses do the opposite: they teach fundamentals as static theory (read the balance sheet, check the P/E) with no code, no real filing, nothing you can run. Neither habit reflects how a serious investor actually works: price is what the market is willing to pay right now; fundamentals are the evidence for whether that price is reasonable.

`yfinance` exposes the same fundamentals data a terminal would, for free, with no broker account: `Ticker.info` (a snapshot dict), `Ticker.financials` / `.quarterly_financials` (income statement), `.balance_sheet`, and `.cashflow`. This chapter pulls real numbers for `NSE_TICKER` and `US_TICKER` side by side — not because Reliance and Apple are comparable businesses, but because comparing a familiar US mega-cap against an Indian large-cap makes it obvious which fundamentals are universal (P/E, margins) and which need local context (currency, sector norms, promoter holding conventions that don't exist for US filings)."""),
        code("""nse = yf.Ticker(NSE_TICKER)
us = yf.Ticker(US_TICKER)

def snapshot(ticker):
    info = ticker.info
    return {
        "marketCap": info.get("marketCap"),
        "trailingPE": info.get("trailingPE"),
        "priceToBook": info.get("priceToBook"),
        "dividendYield": info.get("dividendYield"),
        "profitMargins": info.get("profitMargins"),
        "returnOnEquity": info.get("returnOnEquity"),
        "debtToEquity": info.get("debtToEquity"),
        "sector": info.get("sector"),
        "freeCashflow": info.get("freeCashflow"),
    }

compare = pd.DataFrame({NSE_TICKER: snapshot(nse), US_TICKER: snapshot(us)})
print(compare)
"""),
        md("""## Reading the numbers

- **P/E (price-to-earnings):** what the market is paying per rupee/dollar of last year's profit. High P/E means the market is pricing in growth that hasn't happened yet — that's a bet, not a fact. A "cheap" P/E can just mean the market correctly expects earnings to fall.
- **P/B (price-to-book):** price against accounting net worth. More useful for asset-heavy businesses (banks, manufacturers) than asset-light ones (software), where most of the value is in things a balance sheet doesn't capture.
- **Dividend yield:** cash return, independent of price appreciation. A yield that looks unusually high is often the market pricing in a dividend cut, not a gift.
- **ROE (return on equity):** how efficiently the company turns shareholder capital into profit. High ROE funded by high debt is a different, riskier story than high ROE funded by retained earnings — which is exactly why the next cell doesn't stop at `.info`.
- **Debt/equity:** leverage. `.info`'s cached value can be stale by a quarter or more; the balance sheet below is the primary source."""),
        code("""nse_financials = nse.financials  # annual income statement, most recent period first
if "Total Revenue" in nse_financials.index and nse_financials.loc["Total Revenue"].notna().sum() >= 2:
    revenue = nse_financials.loc["Total Revenue"].dropna()
    yoy_growth = revenue.iloc[0] / revenue.iloc[1] - 1
    print(f"{NSE_TICKER} YoY revenue growth (latest two annual filings): {yoy_growth:.1%}")
else:
    print(f"{NSE_TICKER}: not enough annual revenue history returned to compute YoY growth.")

nse_balance = nse.balance_sheet
if "Total Debt" in nse_balance.index and "Common Stock Equity" in nse_balance.index:
    debt = nse_balance.loc["Total Debt"].iloc[0]
    equity = nse_balance.loc["Common Stock Equity"].iloc[0]
    print(f"{NSE_TICKER} balance-sheet debt/equity (most recent filing): {debt / equity:.2f}")
else:
    print(f"{NSE_TICKER}: balance sheet did not return the expected line items — field names vary by ticker and exchange.")
"""),
        md("""## Where this breaks

- `.info` fields are cached snapshots and vary by ticker — some Indian tickers return fewer fields than US ones, and a missing key means "not reported here," not zero.
- Fundamentals lag price by a full quarter at best; a great balance sheet six months ago says nothing about what changed last week.
- A metric in isolation is close to meaningless. A P/E of 40 is expensive for a slow-growing utility and cheap for a company compounding earnings at 40% a year — you have to compare against the sector and the company's own growth rate (the P/E-to-growth, or PEG, idea), not a fixed threshold.
- None of this predicts price movement on any particular day. Fundamentals answer "is this a business worth owning," not "should I buy in the next five minutes" — that second question is what notebook 27 turns to next, and it comes with its own honesty problem."""),
    ]


def body_27_indicators_tested_honestly():
    return [
        md("""## "This indicator works" is a claim, not a fact

Search for any popular indicator and you'll find one video insisting it's essential and the next calling it useless — both presented with total confidence, neither showing a single line of code. Notebook 21 built all 50 indicators and described what each family measures; it stopped short of asking the harder question: on real data, did any of them actually correlate with what happened next?

This chapter asks that question properly — not to hand you a verdict to memorize, but to show you how to interrogate a claim yourself instead of trusting whoever sounds most confident. The code below computes indicators on real pulled history and tests a few textbook claims against real forward returns."""),
        code("!pip install -q pandas numpy matplotlib\n" + INDICATOR_ENGINE_SRC),
        code("""hist = yf.Ticker(INDEX_TICKER).history(period="5y", interval="1d")
hist = hist.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
print(f"{INDEX_TICKER}: {len(hist)} daily bars, {hist.index.min().date()} to {hist.index.max().date()}")

indicators = compute_top_50(hist)  # column names are case-insensitive on the way in
close = hist["Close"]
print("indicator columns available:", indicators.shape[1])
"""),
        md("""## Testing three textbook claims

- **RSI(14):** "below 30 is oversold, expect a bounce; above 70 is overbought, expect a pullback."
- **MACD:** "a bullish crossover (MACD line crossing above its signal line) marks a shift toward upward momentum."
- **ADX(14):** "above ~25 the market is trending, and trend-following setups do better; below ~20 it's chop."

Each is testable: bucket historical days by the condition, then look at what actually happened over the following N trading days. Note the direction of time here — this is a *retrospective research question* ("did this condition tend to precede that outcome"), which is legitimate to compute with `.shift(-horizon)` on data you already have in front of you. That is different from *lookahead bias inside a backtest*, where a strategy's simulated decision on day T secretly uses information only available after day T. Notebook 29 draws that line precisely — keep it in mind here, because it's easy to blur the two."""),
        code("""horizon = 10  # trading days
forward_return = close.shift(-horizon) / close - 1

rsi = indicators["14_rsi_14"]
oversold = forward_return[rsi < 30]
overbought = forward_return[rsi > 70]
print(f"RSI<30  — {oversold.count():4d} obs, mean {horizon}d forward return {oversold.mean():+.2%}, std {oversold.std():.2%}")
print(f"RSI>70  — {overbought.count():4d} obs, mean {horizon}d forward return {overbought.mean():+.2%}, std {overbought.std():.2%}")
"""),
        code("""macd, signal = indicators["08_macd"], indicators["09_macd_signal"]
bullish_cross = (macd.shift(1) < signal.shift(1)) & (macd > signal)
cross_fwd = forward_return[bullish_cross]
print(f"MACD bullish crossover — {cross_fwd.count():4d} events, mean {horizon}d forward return {cross_fwd.mean():+.2%}, std {cross_fwd.std():.2%}")
"""),
        code("""adx = indicators["37_adx_14"]
trending = forward_return[adx > 25]
choppy = forward_return[adx < 20]
print(f"ADX>25 (trending) — {trending.count():4d} obs, mean {horizon}d forward return {trending.mean():+.2%}, std {trending.std():.2%}")
print(f"ADX<20 (choppy)   — {choppy.count():4d} obs, mean {horizon}d forward return {choppy.mean():+.2%}, std {choppy.std():.2%}")
"""),
        md("""## What this test does — and doesn't — prove

Whatever numbers come out above, treat them as a starting point, not a verdict:

- **One ticker, one history.** These 5 years of Nifty behavior are one sample path out of many that could have happened. A pattern here may be specific to this index, this regime (rate cycle, liquidity conditions), or pure coincidence.
- **Overlapping windows aren't independent observations.** A 10-day forward return computed on every single day overlaps with the 9 days before and after it — the "count" in each bucket wildly overstates how much independent evidence you actually have. Proper statistical testing would need to account for this (block bootstrap, or non-overlapping samples), which this chapter deliberately doesn't do, so as not to imply a rigor it doesn't have.
- **No significance test, no multiple-comparison correction.** We tested three claims; if you tested thirty, some would look good by chance alone even with zero real edge. That's a preview of the overfitting trap notebook 29 demonstrates deliberately.
- **A positive average is necessary, not sufficient.** Even a real, non-random edge has to survive transaction costs, slippage, and regime change before it's tradeable — none of which this notebook has applied yet.

The honest conclusion from a chapter like this is almost never "indicator X works" or "indicator X is useless." It's "here's what the data shows, here's how much I should trust it, and here's what I'd need to check next" — which is a far more useful habit than picking a side in a comments-section argument."""),
    ]


def body_28_options_against_reality():
    return [
        md("""## Most options tutorials price a number nobody checked

Open almost any options-Greeks tutorial and you'll find `spot = 100`, `strike = 105` — clean, round, and disconnected from anything trading right now. That's fine for teaching the shape of a formula, but it hides the part that actually matters in practice: an option's price and Greeks are only as good as the inputs you feed them, and two of those inputs — spot and volatility — are things you should be *measuring*, not guessing.

This notebook fetches a real spot price with yfinance, computes a real historical volatility from real trailing returns, and only then calls the same `bs_price()` / `greeks()` pricer used in notebook 06 — so every number below is anchored to something that existed in the market a moment ago, not a textbook placeholder."""),
        code("""spot_row = yf.Ticker(NSE_TICKER).history(period="5d")
spot = float(spot_row["Close"].iloc[-1])
as_of = spot_row.index[-1].date()
print(f"{NSE_TICKER} last close: {spot:.2f} (as of {as_of})")

us_row = yf.Ticker(US_TICKER).history(period="5d")
us_spot = float(us_row["Close"].iloc[-1])
print(f"{US_TICKER} last close: {us_spot:.2f} (as of {us_row.index[-1].date()})")
"""),
        md("""## Historical volatility vs. implied volatility — not the same number

There are two honest ways to get a volatility input, and they answer different questions:

- **Historical (realized) volatility** looks *backward*. It's the standard deviation of past returns, annualized — a measured fact about what already happened. It's what we compute below.
- **Implied volatility** looks *forward*. It's backed out of an actual option's market price (notebook 12 does this via bisection) — the market's current forecast, which can differ sharply from recent realized volatility right before an event like results or a policy announcement.

Feeding historical volatility into Black-Scholes gives you a *model* price consistent with recent behavior, not a prediction of where the option will actually trade — if the market is pricing in an upcoming catalyst, implied volatility will run ahead of historical volatility, and the gap between the two is itself useful information, not noise."""),
        code("""import numpy as np

def annualized_realized_vol(history, window=30):
    log_ret = np.log(history["Close"] / history["Close"].shift(1)).dropna()
    return float(log_ret.tail(window).std() * np.sqrt(252))

nse_hist = yf.Ticker(NSE_TICKER).history(period="6mo")
hv_30 = annualized_realized_vol(nse_hist, window=30)
hv_90 = annualized_realized_vol(nse_hist, window=90)
print(f"{NSE_TICKER} 30-day realized vol: {hv_30:.1%}")
print(f"{NSE_TICKER} 90-day realized vol: {hv_90:.1%}")
"""),
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

# Round spot to the nearest 50 to pick a realistic near-the-money strike.
strike = round(spot / 50) * 50
t_years = 7 / 365  # a hypothetical weekly expiry, 7 calendar days out

ce_price = bs_price("CE", spot, strike, t_years, hv_30)
ce_greeks = greeks("CE", spot, strike, t_years, hv_30)
print(f"{NSE_TICKER} spot {spot:.2f}, strike {strike}, vol {hv_30:.1%} (30-day realized)")
print("Model CE price:", round(ce_price, 2))
print("Model CE greeks:", {k: round(v, 4) for k, v in ce_greeks.items()})
"""),
        md("""## Reading the Greeks against numbers you just measured

- **Delta** — with spot near the strike (we rounded to the nearest 50 specifically to land close to at-the-money), expect delta near 0.5 for the call. Re-run this notebook on a day when the stock has moved and watch delta shift toward 0 (deep OTM) or 1 (deep ITM) — that's delta *doing its job* as a moneyness gauge, not an abstract Greek in a table.
- **Gamma** — highest exactly where we are, ATM, with 7 days to expiry. If you change `t_years` to something much larger, gamma drops noticeably: gamma concentrates near expiry, which is why index-option desks watch gamma exposure most closely in the final days before a weekly settlement.
- **Theta** — this is a daily decay figure, in the same currency units as `spot`. Multiply by the lot size and by days held to see the actual carry a short seller is collecting (or a long buyer is bleeding) — a much more concrete number than "options decay over time."
- **Vega** — priced off `hv_30`, our historical estimate. If you separately pulled a real implied volatility for this strike (notebook 12) and it's meaningfully higher than `hv_30`, that gap is the market pricing in more uncertainty than recent history alone would suggest — often the case right before earnings or a macro event.

None of this makes Black-Scholes correct — it's still a model with constant-volatility, continuous-trading assumptions that real markets violate. What real spot and real historical volatility buy you is a pricer that's wrong in a *known, measurable* way, instead of wrong in a way you can't even characterize because the inputs were invented."""),
    ]


def body_29_backtesting_honestly():
    return [
        md("""## Notebook 14 said it plainly: "a simplified, cost-free backtest"

Notebook 14 backtests a weekly short straddle and is honest about its own limits in its first cell: no slippage, no costs, no margin, no out-of-sample split. That's a reasonable thing for a *mechanics* demo to skip — but it means notebook 14's P&L number is not evidence of an edge, and most retail backtesting content (free courses especially) stops exactly there, mentioning "backtesting pitfalls" in a bullet list without ever showing you the bug in running code.

This notebook does the opposite: it deliberately writes two classic backtesting mistakes, runs them, and then fixes them — so you can see the difference a subtle bug makes to a P&L curve, not just be told it matters. Then it adds back the two things notebook 14 skipped that matter most in India: transaction costs and an out-of-sample split."""),
        code("""hist = yf.download(NSE_TICKER, period="2y", interval="1d", progress=False, multi_level_index=False)
hist = hist[["Close"]].dropna()
hist.columns = ["close"]
print(f"{NSE_TICKER}: {len(hist)} sessions, {hist.index[0].date()} to {hist.index[-1].date()}")
"""),
        md("""## Bug #1: look-ahead bias — using tomorrow's information today

The strategy: go long when a fast moving average crosses above a slow moving average ("golden cross"), flat otherwise. The **buggy** version below computes the signal, then aligns it to *today's* return using `shift(-1)` on the return series — which quietly hands the strategy tomorrow's closing price before the trading day it's supposed to act on has happened. This is an easy bug to write by accident (off-by-one direction errors in `shift()` are the single most common source of look-ahead bias in pandas backtests) and it always makes the backtest look better than any strategy could actually trade, because the "signal" is partly informed by the outcome it's predicting."""),
        code("""fast, slow = 20, 50
hist["sma_fast"] = hist["close"].rolling(fast).mean()
hist["sma_slow"] = hist["close"].rolling(slow).mean()
hist["signal"] = (hist["sma_fast"] > hist["sma_slow"]).astype(int)
hist["daily_ret"] = hist["close"].pct_change()

# BUGGY: shift(-1) pulls tomorrow's return back onto today's signal —
# the strategy is effectively told the outcome before it "happens."
buggy_strategy_ret = hist["signal"] * hist["daily_ret"].shift(-1)
buggy_equity = (1 + buggy_strategy_ret.fillna(0)).cumprod()
print("Look-ahead-biased final equity multiple:", round(buggy_equity.iloc[-1], 3))
"""),
        md("""## The fix: only trade on information that existed at the time

The correct version uses **today's** signal to decide whether you're positioned for **tomorrow's** move, which means the signal itself must be built from data available *before* the bar it trades — shift the signal forward by one bar, not the return backward. The visible difference between the buggy and corrected equity curves is the entire size of the look-ahead bug — on real data, it is rarely small."""),
        code("""# CORRECT: shift the *signal* forward — trade tomorrow using only
# information known at today's close, never information from tomorrow.
hist["signal_lagged"] = hist["signal"].shift(1)
correct_strategy_ret = hist["signal_lagged"] * hist["daily_ret"]
correct_equity = (1 + correct_strategy_ret.fillna(0)).cumprod()
print("Look-ahead-corrected final equity multiple:", round(correct_equity.iloc[-1], 3))
print("Buy-and-hold final equity multiple:        ", round((1 + hist['daily_ret'].fillna(0)).cumprod().iloc[-1], 3))
"""),
        md("""## Bug #2: overfitting — picking the window that happened to win

A moving-average crossover has a free parameter: the window lengths. Grid-searching many window pairs against a fixed historical period and reporting the single best result as "the strategy's edge" is curve-fitting, not strategy design — you are, by construction, selecting for whichever parameter combination happened to fit *this specific* noise, which is not the same thing as a persistent, tradeable pattern."""),
        code("""results = []
for fast_w in range(5, 41, 5):
    for slow_w in range(50, 121, 10):
        if fast_w >= slow_w:
            continue
        sig = (hist["close"].rolling(fast_w).mean() > hist["close"].rolling(slow_w).mean()).astype(int)
        ret = sig.shift(1) * hist["daily_ret"]
        equity_mult = (1 + ret.fillna(0)).cumprod().iloc[-1]
        results.append({"fast": fast_w, "slow": slow_w, "equity_mult": equity_mult})

grid = pd.DataFrame(results).sort_values("equity_mult", ascending=False)
print("Best in-sample combination (DO NOT trust this number yet):")
print(grid.head(3))
"""),
        md("""## The fix: a walk-forward split — validate on data the search never saw

Split the history into a **train** window (search for the best parameters here) and a **held-out test** window (evaluate — do not re-tune — on this). If the parameter combination that won on the train window doesn't hold up on the untouched test window, the "edge" the grid search found was fit to noise in the train period, not a real, persistent pattern. This is the minimum bar for treating a backtest result as evidence rather than a coincidence; a real research process goes further with multiple rolling train/test folds, but even a single honest split catches the most common failure mode."""),
        code("""split_idx = int(len(hist) * 0.7)
train, test = hist.iloc[:split_idx], hist.iloc[split_idx:]

def equity_mult_for(frame, fast_w, slow_w):
    sig = (frame["close"].rolling(fast_w).mean() > frame["close"].rolling(slow_w).mean()).astype(int)
    ret = sig.shift(1) * frame["close"].pct_change()
    return float((1 + ret.fillna(0)).cumprod().iloc[-1])

best_fast, best_slow = int(grid.iloc[0]["fast"]), int(grid.iloc[0]["slow"])
train_mult = equity_mult_for(train, best_fast, best_slow)
test_mult = equity_mult_for(test, best_fast, best_slow)
print(f"Best train-window combo ({best_fast}/{best_slow}) — train equity mult: {train_mult:.3f}")
print(f"Same combo, held-out test window        — test equity mult:  {test_mult:.3f}")
print("A test result that's dramatically worse than train is the walk-forward split doing its job.")
"""),
        md("""## What notebook 14 left out: real transaction costs

India-specific costs that a gross P&L number ignores entirely: **STT** (securities transaction tax — charged differently for equity delivery, intraday and F&O, and rates change by government notification, so verify the current rate on the NSE/SEBI circular before using this for real sizing, don't trust a number in a training notebook), **brokerage** per executed order, exchange transaction charges, and **slippage** — the gap between the price your signal used and the price you actually got filled at, which is usually small for a large-cap NSE stock and can be large for anything illiquid.

The mechanism below is a flat cost-per-trade assumption, deliberately conservative and easy to swap for real numbers from your own broker's contract note."""),
        code("""# Illustrative flat-cost assumption — replace with your broker's actual
# brokerage + STT + exchange charges before drawing any real conclusion.
cost_per_trade_pct = 0.001  # 0.10% round-trip, placeholder — verify real STT/brokerage rates

trades = hist["signal_lagged"].diff().fillna(0) != 0  # a trade happens whenever the position changes
n_trades = int(trades.sum())
gross_mult = correct_equity.iloc[-1]
cost_drag = n_trades * cost_per_trade_pct
net_mult = gross_mult * (1 - cost_drag)

print(f"Trades over the period: {n_trades}")
print(f"Gross equity multiple (no costs):   {gross_mult:.3f}")
print(f"Net equity multiple (with costs):   {net_mult:.3f}")
print("A strategy that trades often can look profitable gross and lose money net — "
      "the more frequently a signal flips, the more this gap matters.")
"""),
        md("""## Putting it together

Every fix in this notebook — lagging the signal correctly, validating on a held-out window, and subtracting real costs — makes a backtest *less* impressive and *more* trustworthy. That trade is the entire point: notebook 14's cost-free, single-window straddle backtest is a fine way to check that payoff mechanics are wired correctly, but treat any backtest result, including the ones in this series, as a hypothesis to keep stress-testing, not a number to size real capital against."""),
    ]


def body_30_position_sizing_psychology():
    return [
        md("""## "Risk 1-2% per trade" is usually asserted, never shown

Every trading course repeats some version of this rule. Almost none of them show you why the number matters, because that requires simulating many possible sequences of wins and losses and watching what position size does to the *tail* of the outcome distribution — not just its average. This is the same distinction notebook 15 makes between expected value and risk of ruin, but here it's run as an actual Monte Carlo instead of stated as a maxim.

**The setup.** A real trading strategy has its own win rate and average win/loss ratio, ideally measured from its own backtest (notebook 29). As a reproducible stand-in, this notebook derives a win rate and payoff ratio from the real index's up-day vs. down-day history — the index doesn't know or care about position sizing, so it's a clean, real-data source of "how often do you win, and by how much relative to a loss" without hand-picking numbers to make a point. Each simulated "trade" then risks a fixed fraction of *current* equity, wins with that empirical probability, and either gains `risk_pct × payoff_ratio` or loses `risk_pct`.

**Ruin isn't "the strategy loses money."** It's a large enough drawdown that recovery becomes mathematically or psychologically implausible — losing 50% requires a 100% gain just to get back to even. The simulation below runs thousands of independent trade sequences per risk level and reports the fraction of paths that ever cross that floor. Watch how a strategy that looks perfectly reasonable in expectation can still ruin a meaningful share of accounts once you size it too aggressively — and how that share does not scale linearly with risk_pct."""),
        code("""hist = yf.download(INDEX_TICKER, period="2y", interval="1d", progress=False, auto_adjust=True, multi_level_index=False)
daily_returns = hist["Close"].pct_change().dropna()
ann_vol = float(daily_returns.std() * np.sqrt(252))
print(f"{INDEX_TICKER} trailing 2y annualized volatility: {ann_vol:.1%}")

wins = daily_returns[daily_returns > 0]
losses = daily_returns[daily_returns < 0]
win_rate = float(len(wins) / len(daily_returns))
payoff_ratio = float(wins.mean() / abs(losses.mean()))
print(f"Empirical up-day rate: {win_rate:.1%}   avg-up / avg-down ratio: {payoff_ratio:.2f}")
print("(a real strategy should use its own win rate / payoff ratio from notebook 29, not the raw index)")

rng = np.random.default_rng(42)
N_PATHS, N_TRADES, RUIN_FLOOR = 3000, 250, 0.5   # ruin = equity falls below 50% of starting capital

def simulate(risk_pct, revenge_multiplier=None, cap=0.20):
    \"\"\"Fixed-fractional sizing. If revenge_multiplier is set, risk doubles
    (up to `cap`) after every loss and resets to risk_pct after every win —
    the classic 'get back to even' behavioral deviation.\"\"\"
    equity = np.ones(N_PATHS)
    ruined = np.zeros(N_PATHS, dtype=bool)
    current_risk = np.full(N_PATHS, risk_pct)
    for _ in range(N_TRADES):
        win = rng.random(N_PATHS) < win_rate
        step = np.where(win, current_risk * payoff_ratio, -current_risk)
        equity = np.clip(equity * (1 + step), 0, None)
        ruined |= equity < RUIN_FLOOR
        if revenge_multiplier is not None:
            current_risk = np.where(win, risk_pct, np.minimum(current_risk * revenge_multiplier, cap))
    return equity, ruined

print("\\n-- Position size vs. risk of ruin (disciplined fixed-fractional) --")
for risk_pct in (0.01, 0.02, 0.05, 0.10):
    equity, ruined = simulate(risk_pct)
    print(f"risk_pct={risk_pct:>4.0%}  median ending equity={np.median(equity):.2f}x start  "
          f"P(ruin)={ruined.mean():.1%}")
"""),
        md("""## Quantifying a psychological mistake, not just naming it

Trading-psychology material — Zerodha Varsity's Innerworth module is a good example — correctly identifies behaviors like revenge trading ("double the size to get back to even after a loss") or moving a stop-loss further away mid-trade ("give it more room, it'll come back"). What it doesn't do is put a number on what that behavior costs, so the warning stays abstract and easy to ignore under real drawdown stress.

The simulation below runs the *identical* trade-generating process from above twice, at the same starting `risk_pct`: once with strict fixed-fractional sizing, once with a "revenge" rule that doubles risk after every loss (capped so it can't reach 100% in one trade) and resets after a win. Same win rate, same payoff ratio, same number of trades — the only variable is whether position size is allowed to react emotionally to the last outcome."""),
        code("""disciplined_eq, disciplined_ruin = simulate(0.02)
revenge_eq, revenge_ruin = simulate(0.02, revenge_multiplier=2.0)

print("-- Same 250-trade sequence, disciplined vs. revenge-sized --")
print(f"Disciplined 2% fixed risk : median {np.median(disciplined_eq):.2f}x start   P(ruin)={disciplined_ruin.mean():.1%}")
print(f"Same rule + revenge sizing: median {np.median(revenge_eq):.2f}x start   P(ruin)={revenge_ruin.mean():.1%}")
print("\\nSame edge, same market — the only difference is whether size reacted to the last loss.")
"""),
        md("""## The fix is mechanical, not motivational

Notice that `guard_max_loss()` in notebook 15 is a hard `raise`, not a warning — and now you've seen why that design choice matters more than it looks. A rule that can be overridden in the moment ("just this once, I'll size up — I'm confident") is not a rule; it's a suggestion that fails exactly when a real strategy's variance puts it under the most pressure, which is precisely the moment simulated above where revenge sizing does the most damage. Position sizing discipline that survives contact with a real drawdown is enforced by code or a broker-side hard limit, not by remembering to be calm."""),
    ]


def body_31_school_capstone():
    return [
        md(f"""## The Stock Market School, end to end

Chapters 24-30 each covered one link in a chain, all on real data pulled live via yfinance — no ServLoci account needed to run any of it:

1. **Reading the market (24)** — pull real OHLCV for an NSE stock, a US stock, and an index; understand adjusted close, dividends, splits.
2. **Returns & risk (25)** — turn a price series into annualized return, volatility, Sharpe/Sortino and max drawdown.
3. **Fundamentals (26)** — P/E, market cap, debt/equity as a sanity filter, not a signal on their own.
4. **Indicators, tested (27)** — compute a technical signal and actually check whether it correlates with forward returns, instead of trusting it by default.
5. **Options against reality (28)** — price and Greek an option off a real fetched spot, not a textbook number.
6. **Honest backtesting (29)** — lag signals correctly, hold out a test window, subtract real costs.
7. **Risk of ruin (30)** — size the position so a normal losing streak doesn't end the account, and see what happens when sizing gets emotional instead.

This capstone runs a condensed version of that whole chain on one real ticker, then prints a single decision-chain report — the same shape every stage above justified separately."""),
        code("""data = yf.download(NSE_TICKER, period="3y", interval="1d", progress=False, auto_adjust=True, multi_level_index=False)
close = data["Close"]
returns = close.pct_change().dropna()
ann_return = float(returns.mean() * 252)
ann_vol = float(returns.std() * np.sqrt(252))
sharpe = ann_return / ann_vol if ann_vol else float("nan")
print(f"[1] {NSE_TICKER}: annualized return {ann_return:.1%}, volatility {ann_vol:.1%}, Sharpe {sharpe:.2f}")
"""),
        code("""info = yf.Ticker(NSE_TICKER).info
pe = info.get("trailingPE")
market_cap = info.get("marketCap")
# Crude sanity band, not investment advice — a filter to skip obviously broken
# or unpriceable names, not a ranking of good vs. bad companies.
passes_fundamentals = pe is not None and 0 < pe < 60
print(f"[2] {NSE_TICKER}: trailing P/E={pe}, market cap={market_cap}, passes basic sanity filter={passes_fundamentals}")
"""),
        code("""sma_fast = close.rolling(20).mean()
sma_slow = close.rolling(50).mean()
cross = (sma_fast > sma_slow).astype(int).diff().fillna(0)
forward_5d_return = close.shift(-5) / close - 1

golden_cross_days = cross[cross == 1].index
if len(golden_cross_days):
    edge = float(forward_5d_return.reindex(golden_cross_days).mean())
    print(f"[3] Golden-cross days: {len(golden_cross_days)}, avg forward 5-day return: {edge:.2%}")
else:
    print("[3] No golden-cross signals in this window — see notebook 27 before trusting any single signal.")
"""),
        code(BS_PRICE_SRC + """
spot = float(close.iloc[-1])
strike = round(spot / 50) * 50  # nearest 50-point strike, illustrative only
premium = bs_price("CE", spot, strike, t_years=7 / 365, vol=ann_vol)
print(f"[4] Illustrative ATM {strike} CE, 7 DTE, {ann_vol:.0%} vol -> Black-Scholes premium Rs.{premium:.2f}")
"""),
        code("""STT_SELL = 0.001            # simplified equity-delivery STT approximation — confirm current rate before sizing real capital
BROKERAGE_PER_TRADE = 20    # flat per-order brokerage, typical Indian discount-broker cap

split = int(len(close) * 0.7)
train, test = close.iloc[:split], close.iloc[split:]

def backtest_sma_crossover(prices, fast=20, slow=50, capital=100_000):
    sma_f = prices.rolling(fast).mean()
    sma_s = prices.rolling(slow).mean()
    position = (sma_f > sma_s).astype(int)
    daily_ret = prices.pct_change().fillna(0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    n_trades = int(position.diff().abs().fillna(0).sum())
    cost_drag = n_trades * (BROKERAGE_PER_TRADE / capital + STT_SELL)
    gross_return = float((1 + strat_ret).prod() - 1)
    return {"n_trades": n_trades, "gross_return": gross_return, "cost_drag": cost_drag, "net_return": gross_return - cost_drag}

train_result = backtest_sma_crossover(train)
test_result = backtest_sma_crossover(test)
print("[5] Train (in-sample): ", train_result)
print("[5] Test (out-of-sample):", test_result)
"""),
        code("""def position_size(capital, risk_pct, max_loss_per_share):
    if max_loss_per_share <= 0:
        return 0
    return max(int((capital * risk_pct) // max_loss_per_share), 0)

def guard_max_loss(strategy_max_loss, capital, hard_cap_pct=0.05):
    if abs(strategy_max_loss) > capital * hard_cap_pct:
        raise ValueError(f"strategy max loss {strategy_max_loss} exceeds hard cap {capital * hard_cap_pct}")
    return True

capital, risk_pct = 500_000, 0.02
assumed_max_loss_per_share = spot * 0.05  # illustrative 5% adverse-move assumption, not a stop-loss guarantee
qty = position_size(capital, risk_pct, assumed_max_loss_per_share)
guard_max_loss(qty * assumed_max_loss_per_share, capital)
print(f"[6] Risk-managed size for {NSE_TICKER}: {qty} shares, max assumed loss Rs.{qty * assumed_max_loss_per_share:,.0f}")

print("\\n=== Decision chain summary ===")
print(f"Ticker:               {NSE_TICKER}")
print(f"Annualized Sharpe:     {sharpe:.2f}")
print(f"Fundamentals sanity:   {'PASS' if passes_fundamentals else 'FAIL'}")
print(f"Out-of-sample net ret: {test_result['net_return']:.2%} over {test_result['n_trades']} trades")
print(f"Risk-managed size:     {qty} shares (2% risk budget)")
print("Status:                PAPER / DRY-RUN ONLY — no live order placed")
"""),
        md(f"""## From here to a live system — and why this stops short of one

Everything above ran on public data with no broker account. Turning it into live automation means three things this capstone deliberately left out: a real broker session over a whitelisted static IP (notebooks 00-05), an order management layer that owns retries and idempotency instead of calling a broker endpoint directly (notebook 16), and a signal-to-dispatch boundary that can reject a bad decision before it becomes an order (notebook 18) — with real slippage, real fills, and real brokerage/STT/margin replacing every "illustrative" number used here.

That gap is intentional, not an oversight. Every backtest in this school, including [5] above, is a hypothesis about the past, not a guarantee about the future — and every risk-of-ruin number in notebook 30 assumed a win rate and payoff ratio that a live strategy has to *earn* through its own track record, not borrow from an index. Moving from this capstone to real capital is a separate, deliberate decision that needs its own risk review, monitoring for when live behavior diverges from the backtest, and capital you can afford to lose while you find out where the model was wrong.

Keep building at [{SITE}/tools/strategy-builder]({SITE}/tools/strategy-builder), or grab your own static IP at [{SITE}/register]({SITE}/register) when you're ready to connect this to a broker."""),
    ]


# ── Stock lab (yfinance): correlation, prediction, portfolio ───────────
# Chapters 32-34. Same yfinance_setup_cells() as 24-31. Ideas adapted from
# widely copied Kaggle / OSS notebooks, rewritten so they run on a live
# basket and stay honest about leakage, unstable correlation, and in-sample
# optimisation. We do not vendor other people's notebooks.

BASKET = {
    "RELIANCE.NS": "Reliance",
    "TCS.NS": "TCS",
    "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS": "Infosys",
    "ICICIBANK.NS": "ICICI Bank",
    "BHARTIARTL.NS": "Airtel",
    "SBIN.NS": "SBI",
    "ITC.NS": "ITC",
    "LT.NS": "L&T",
    "^NSEI": "Nifty 50",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
}


def body_32_correlation_and_pairs():
    return [
        md("""## Correlation is a fact about *this* window, not a law

Kaggle stock-analysis notebooks almost all draw the same picture: download a handful of names, plot a `seaborn` heatmap of return correlations, and declare that "these stocks move together." That picture is useful — and routinely over-read.

This chapter does the useful part on a live NSE + US basket, then the part those notebooks skip: rolling correlation (it is not stable), a pair that looks "hedgeable" until a crash week, and why a 0.85 correlation is **not** two independent bets.

**Sources this chapter is in conversation with** (read them, don't paste them):

- [Stock Market Analysis Using Python](https://www.kaggle.com/code/krutikashimpi/stock-market-analysis-using-python) — AAPL/GOOG/AMZN/MSFT tour, daily returns, heatmap.
- [Stocks Analysis by Regression](https://www.kaggle.com/code/kausik123/stocks-analysis-by-regression) — scatter matrix + correlation as a prelude to regression.
- [Yahoo Finance: Optimized Portfolio & CAPM](https://www.kaggle.com/code/amitvkulkarni/yahoo-finance-building-optimized-portfolio-capm) — heatmap then jumps to CAPM / weights (notebook 34).
- [Stock Performance with Yahoo Finance](https://www.kaggle.com/code/asimislam/stock-performance-with-yahoo-finance-yfinance) — long-history yfinance pull and relative performance.

None of those is a pair-trading system. Neither is this."""),
        code("""!pip install -q matplotlib
import matplotlib.pyplot as plt

BASKET = {
    "RELIANCE.NS": "Reliance", "TCS.NS": "TCS", "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS": "Infosys", "ICICIBANK.NS": "ICICI Bank", "BHARTIARTL.NS": "Airtel",
    "SBIN.NS": "SBI", "ITC.NS": "ITC", "LT.NS": "L&T", "^NSEI": "Nifty 50",
    "AAPL": "Apple", "MSFT": "Microsoft",
}

raw = yf.download(
    list(BASKET), period="3y", interval="1d",
    auto_adjust=True, progress=False, group_by="ticker", threads=True,
)

def close_of(symbol):
    if isinstance(raw.columns, pd.MultiIndex):
        if symbol not in raw.columns.get_level_values(0):
            return pd.Series(dtype=float, name=symbol)
        frame = raw[symbol]
        col = "Close" if "Close" in frame.columns else frame.columns[0]
        return frame[col].rename(symbol)
    return raw[symbol].rename(symbol) if symbol in raw.columns else raw["Close"].rename(symbol)

prices = pd.concat([close_of(s) for s in BASKET], axis=1).dropna(how="all")
prices.columns = [BASKET[c] for c in prices.columns]
returns = prices.pct_change(fill_method=None).dropna(how="any")
print("aligned sessions:", len(returns), returns.index.min().date(), "->", returns.index.max().date())
print("names:", list(returns.columns))
returns.tail(3)
"""),
        md("""## Full-sample correlation heatmap

This is the chart every Kaggle market notebook leads with. Read it as "how much of the daily move was shared *over this whole 3-year window*," not "these two names are the same bet tomorrow." Banks will cluster. Infosys and TCS will cluster. Apple and Microsoft will cluster. ITC often looks like the diversifier — until it doesn't."""),
        code("""corr = returns.corr()
fig, ax = plt.subplots(figsize=(8.5, 7))
im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
ax.set_xticks(range(len(corr.columns)))
ax.set_yticks(range(len(corr.columns)))
ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
ax.set_yticklabels(corr.columns, fontsize=8)
for i in range(len(corr)):
    for j in range(len(corr)):
        ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=7,
                color="white" if abs(corr.values[i, j]) > 0.65 else "#1a1a1a")
fig.colorbar(im, ax=ax, fraction=0.046)
ax.set_title("Daily-return correlation, full sample")
fig.tight_layout()
plt.show()
print("highest off-diagonal pairs:")
pairs = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool)).stack().sort_values(ascending=False)
print(pairs.head(8).to_string())
print("\\nlowest pairs (closest to diversifiers):")
print(pairs.tail(5).to_string())
"""),
        md("""## Rolling correlation — the heatmap is a freeze-frame

A 60-session rolling correlation of two "tight" names against the index usually drifts. Crisis weeks it jumps toward 1: everything falls together, which is exactly when you wanted the diversifier. That is why a portfolio built on a single full-sample matrix (notebook 34) looks safer than it is."""),
        code("""window = 60
nifty = returns["Nifty 50"] if "Nifty 50" in returns.columns else returns.iloc[:, 0]
roll = pd.DataFrame({
    name: returns[name].rolling(window).corr(nifty)
    for name in returns.columns if name != nifty.name
})
fig, ax = plt.subplots(figsize=(11, 4))
for col in roll.columns:
    ax.plot(roll.index, roll[col], lw=1, label=col)
ax.axhline(0, color="#999", lw=0.6)
ax.set_title(f"{window}-session rolling correlation vs {nifty.name}")
ax.legend(loc="upper left", fontsize=7, ncol=3, frameon=False)
ax.set_ylim(-0.2, 1.05)
ax.grid(True, alpha=0.25)
fig.tight_layout()
plt.show()
print(roll.tail(1).T.rename(columns={roll.index[-1]: "latest_vs_index"}))
"""),
        md("""## A pair is not a hedge

Pick the tightest NSE pair from the matrix. Their *spread* of log prices looks mean-reverting on a quiet chart and then steps when one name has a stock-specific week (results, a block deal, a sector news item the other name does not share). The Kaggle move is to regress one on the other and call the residual a "spread." Residual ≠ tradable hedge: beta is estimated in-sample, the legs have different borrow/impact, and the relationship breaks on the week you need it."""),
        code("""# Tightest pair that is not the index and not the same listing twice.
pair_names = [a for a, b in pairs.index if a != "Nifty 50" and b != "Nifty 50"]
left, right = pairs.index[0]
# pairs.index entries are (row, col) labels; prefer two Indian names if present.
for a, b in pairs.index:
    if a != "Nifty 50" and b != "Nifty 50" and a != b:
        left, right = a, b
        break
print(f"inspecting pair: {left} vs {right}  (full-sample corr {corr.loc[left, right]:.2f})")
spread = np.log(prices[left]) - np.log(prices[right])
z = (spread - spread.rolling(60).mean()) / spread.rolling(60).std()
fig, axes = plt.subplots(2, 1, figsize=(11, 5), sharex=True)
axes[0].plot(prices.index, prices[left] / prices[left].iloc[0], label=left)
axes[0].plot(prices.index, prices[right] / prices[right].iloc[0], label=right)
axes[0].legend(frameon=False)
axes[0].set_title("Rebased prices (start = 1)")
axes[1].plot(z.index, z, color="#0f766e", lw=1)
axes[1].axhline(2, color="#b45309", ls="--", lw=0.8)
axes[1].axhline(-2, color="#b45309", ls="--", lw=0.8)
axes[1].set_title("60-session z-score of log spread — looks tradable, is not a system")
axes[1].grid(True, alpha=0.25)
fig.tight_layout()
plt.show()
print("z-score now:", float(z.iloc[-1]) if pd.notna(z.iloc[-1]) else "warming up")
"""),
        md("""## What to take into notebook 34

- Names that cluster on the heatmap are **overlapping bets**. Equal-weighting five bank stocks is not five-name diversification.
- Rolling correlation vs the index is the honest "how much systematic risk is this name carrying right now."
- A z-score on a spread is a research plot. Turning it into a pair trade needs borrow, beta stability, and a stop for when the residual is a company event, not noise.

Next: notebook 33 — the other Kaggle genre, "I predicted the stock with LSTM," rewritten so the naive baseline has to lose first."""),
    ]


def body_33_prediction_baselines():
    return [
        md("""## Most "stock prediction" notebooks predict yesterday

The most-copied Kaggle notebook in this genre is [Stock Market Analysis + Prediction using LSTM](https://www.kaggle.com/code/faressayah/stock-market-analysis-prediction-using-lstm) (Fares Sayah): 60 days of prices in, next day's *price* out, a line chart that hugs the actual series, impressive-looking RMSE.

That chart is usually a visual trick. Prices are a random-ish walk plus drift. A model that outputs "tomorrow ≈ today" will overlay almost perfectly on a price plot and still have **no trading edge**. Related copies use SVR / Random Forest / KNN / Prophet on the same leaked setup:

- [Advanced stock prediction using SVR, RFR, KNN, LSTM](https://www.kaggle.com/general/266594)
- [Yahoo Stock Forecasting 60 Days | LSTM | ARIMA | Prophet](https://www.kaggle.com/code/gamzeakkurt/yahoo-stock-forecasting-60-days-lstm-arima-prophet)

This chapter does not train an LSTM. It does the test those notebooks skip: a **naive** forecast (tomorrow's return = 0, tomorrow's price = today's close) on a **time-ordered** split, then a linear model and a small Random Forest that are only allowed to see information available at the close of day T to forecast the return of day T+1.

If they cannot beat naive on *returns*, they are not predictors. They are smoothers."""),
        code("""!pip install -q scikit-learn matplotlib
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

hist = yf.download(
    NSE_TICKER, period="5y", interval="1d",
    auto_adjust=True, progress=False, multi_level_index=False,
)
close = hist["Close"].dropna()
ret = close.pct_change(fill_method=None)
print(f"{NSE_TICKER}: {len(close)} sessions, {close.index.min().date()} -> {close.index.max().date()}")
"""),
        md("""## Feature frame — only lags, no future

`ret_fwd` is tomorrow's return, the thing we are allowed to forecast. Features are lags of return plus a few trailing statistics. No `shift(-1)` on a feature. No shuffled `train_test_split`. The first 70% of *time* is train; the last 30% is test."""),
        code("""feat = pd.DataFrame({"ret": ret})
for lag in (1, 2, 3, 5, 10):
    feat[f"lag_{lag}"] = ret.shift(lag)
feat["vol_20"] = ret.rolling(20).std()
feat["mom_10"] = close.pct_change(10)
feat["ret_fwd"] = ret.shift(-1)
feat = feat.dropna()

split = int(len(feat) * 0.70)
train, test = feat.iloc[:split], feat.iloc[split:]
x_cols = [c for c in feat.columns if c != "ret_fwd"]
X_train, y_train = train[x_cols], train["ret_fwd"]
X_test, y_test = test[x_cols], test["ret_fwd"]
print(f"train {train.index.min().date()} -> {train.index.max().date()}  ({len(train)} rows)")
print(f"test  {test.index.min().date()} -> {test.index.max().date()}  ({len(test)} rows)")
print("features:", x_cols)
"""),
        md("""## Three forecasts, one honest scoreboard

- **Naive:** predict 0 return (price unchanged). This is the LSTM-hugging-the-price-chart in return space.
- **Linear:** ordinary least squares on the lag features.
- **Forest:** 200 shallow trees. Easy to overfit; we keep `max_depth=4` on purpose.

Score on **returns**, not prices. Then, only for the picture people expect, reconstruct a price path from the predicted returns so you can see how "almost the same line" still happens."""),
        code("""naive = pd.Series(0.0, index=y_test.index)
lin = LinearRegression().fit(X_train, y_train)
pred_lin = pd.Series(lin.predict(X_test), index=y_test.index)
rf = RandomForestRegressor(n_estimators=200, max_depth=4, random_state=7, n_jobs=-1)
rf.fit(X_train, y_train)
pred_rf = pd.Series(rf.predict(X_test), index=y_test.index)

def score(name, pred):
    mae = mean_absolute_error(y_test, pred)
    rmse = mean_squared_error(y_test, pred) ** 0.5
    # Directional accuracy is what a long/short rule would actually use.
    mask = y_test != 0
    direction = float((np.sign(pred[mask]) == np.sign(y_test[mask])).mean()) if mask.any() else float("nan")
    return {"model": name, "MAE": mae, "RMSE": rmse, "dir_acc": direction}

board = pd.DataFrame([
    score("naive (0 return)", naive),
    score("linear lags", pred_lin),
    score("random forest", pred_rf),
])
print(board.to_string(index=False))
print()
print("If MAE/RMSE are not clearly better than naive, the model has no forecast content.")
print("dir_acc near 0.50 is a coin flip. 0.53 on one test window is not a strategy.")
print("linear intercept:", float(lin.intercept_), "  coefs:")
print(pd.Series(lin.coef_, index=x_cols).sort_values(key=np.abs, ascending=False).head(6))
"""),
        md("""## Why the price overlay looks "accurate" anyway

Start from the first test close and compound each model's predicted return. The three lines will sit on top of the actual price path if predicted returns are small — which they are, because daily moves are a few tenths of a percent and every cautious model shrinks toward zero. That is the Fares Sayah chart, without the LSTM."""),
        code("""start = float(close.loc[y_test.index[0]])
actual_path = (1 + y_test).cumprod() * start
naive_path = (1 + naive).cumprod() * start
lin_path = (1 + pred_lin).cumprod() * start
rf_path = (1 + pred_rf).cumprod() * start

fig, axes = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True,
                         gridspec_kw={"height_ratios": [2, 1]})
axes[0].plot(actual_path.index, actual_path, color="#1a1a1a", lw=1.2, label="Actual")
axes[0].plot(naive_path.index, naive_path, color="#94a3b8", lw=1, label="Naive (0 ret)")
axes[0].plot(lin_path.index, lin_path, color="#2563eb", lw=1, label="Linear")
axes[0].plot(rf_path.index, rf_path, color="#7c3aed", lw=1, label="Forest")
axes[0].set_title(f"{NSE_TICKER} test window — price reconstructed from predicted returns")
axes[0].legend(frameon=False, fontsize=8)
axes[0].grid(True, alpha=0.25)
axes[1].plot(y_test.index, y_test, color="#1a1a1a", lw=0.8, label="actual return")
axes[1].plot(pred_lin.index, pred_lin, color="#2563eb", lw=0.8, label="linear pred")
axes[1].set_title("Same window in return space — this is where the model has to win")
axes[1].legend(frameon=False, fontsize=8)
axes[1].grid(True, alpha=0.25)
fig.tight_layout()
plt.show()
"""),
        md("""## What those Kaggle notebooks get wrong, in one list

- **Predicting price, scoring price.** A walk-plus-drift series makes any "tomorrow ≈ today" model look like a fit. Score returns, or score a trading rule after costs (notebook 29).
- **Shuffled train/test.** `train_test_split` without `shuffle=False` leaks the future into the past.
- **Window leakage.** Using a scaler fit on the whole series, or a 60-day window that includes the target day, is the same bug with more lines of Keras.
- **No naive baseline.** If you did not print the zero-return MAE, you do not know whether you beat a coin that always says "unchanged."
- **One ticker, one split.** A 3-point directional edge on Reliance's last 18 months is not a result. It is a number that will move when you change the date.

A real forecast research project starts where this notebook ends: walk-forward folds, costs, a rule that can be flat, and a pre-declared test window you are not allowed to peek at while you "tune." Notebook 29 is that discipline applied to a simpler rule.

Next: notebook 34 — many names at once, weights, an efficient-frontier cloud, and why the "optimal" portfolio on this sample is not a recommendation."""),
    ]


def body_34_portfolio_analytics():
    return [
        md("""## A portfolio is a set of weights, not a list of tickers

Kaggle "optimized portfolio" notebooks usually: download 8–15 names, print a correlation heatmap (notebook 32), throw 5,000 random weights at the cloud, circle the max-Sharpe point, and stop. The better ones then call [PyPortfolioOpt](https://github.com/PyPortfolioOpt/PyPortfolioOpt) (`EfficientFrontier.max_sharpe`, HRP, Black-Litterman).

Worth reading, then rewriting:

- [Yahoo Finance: Building Optimized Portfolio & CAPM](https://www.kaggle.com/code/amitvkulkarni/yahoo-finance-building-optimized-portfolio-capm)
- [Portfolio Optimization — MC and PyPortfolioOpt](https://www.kaggle.com/code/xxxxyyyy80008/portfolio-optimization-mc-and-pyportfolioopt)
- [PortfolioDesign using Efficient Frontier & K-Means](https://www.kaggle.com/code/jaison14/portfoliodesign-using-efficient-frontier-k-means)
- [PyPortfolioOpt cookbook](https://github.com/PyPortfolioOpt/PyPortfolioOpt/tree/master/cookbook) — the clean OSS reference, especially `2-Mean-Variance-Optimisation.ipynb`

This chapter does the Monte Carlo frontier **without** an extra optimiser dependency, then compares three honest baselines: equal weight, inverse-volatility, and the in-sample max-Sharpe point. The last one will look best. That is the trap — it was chosen on the same data you are scoring."""),
        code("""!pip install -q matplotlib
import matplotlib.pyplot as plt

PORTFOLIO = {
    "RELIANCE.NS": "Reliance", "TCS.NS": "TCS", "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS": "Infosys", "ICICIBANK.NS": "ICICI Bank", "BHARTIARTL.NS": "Airtel",
    "ITC.NS": "ITC", "LT.NS": "L&T", "SBIN.NS": "SBI",
}
raw = yf.download(
    list(PORTFOLIO), period="3y", interval="1d",
    auto_adjust=True, progress=False, group_by="ticker", threads=True,
)

def close_of(symbol):
    if isinstance(raw.columns, pd.MultiIndex):
        frame = raw[symbol]
        col = "Close" if "Close" in frame.columns else frame.columns[0]
        return frame[col].rename(symbol)
    return raw[symbol].rename(symbol)

prices = pd.concat([close_of(s) for s in PORTFOLIO], axis=1).dropna(how="any")
prices.columns = [PORTFOLIO[c] for c in prices.columns]
returns = prices.pct_change(fill_method=None).dropna()
mu = returns.mean() * 252
cov = returns.cov() * 252
print(f"{len(returns)} sessions, {returns.index.min().date()} -> {returns.index.max().date()}")
print("annualized mean returns (%):")
print((mu * 100).round(1).to_string())
"""),
        md("""## Three weighting rules

- **Equal weight.** 1/N. No estimate, no in-sample gift.
- **Inverse volatility.** Weight ∝ 1/σ. Cuts the jumpy names without estimating expected return (expected return is the noisiest input in Markowitz).
- **Max Sharpe (in-sample).** Search random long-only weights; keep the best Sharpe on *this* 3-year window. This is the Kaggle circle. It is also a description of the past."""),
        code("""rng = np.random.default_rng(7)
n_assets = returns.shape[1]
rf = 0.06  # illustrative INR cash rate, not a forecast

def stats(weights):
    weights = np.asarray(weights, dtype=float)
    weights = weights / weights.sum()
    ret = float(weights @ mu.values)
    vol = float(np.sqrt(weights @ cov.values @ weights))
    sharpe = (ret - rf) / vol if vol else float("nan")
    return weights, ret, vol, sharpe

eq_w, eq_r, eq_v, eq_s = stats(np.ones(n_assets))
inv_w, inv_r, inv_v, inv_s = stats(1 / returns.std().values)

n_pts = 4000
rand_w = rng.dirichlet(np.ones(n_assets), size=n_pts)
rand_r = rand_w @ mu.values
rand_v = np.sqrt(np.einsum("ij,jk,ik->i", rand_w, cov.values, rand_w))
rand_s = (rand_r - rf) / rand_v
best = int(np.nanargmax(rand_s))
ms_w, ms_r, ms_v, ms_s = stats(rand_w[best])

alloc = pd.DataFrame({
    "equal": eq_w, "inv_vol": inv_w, "max_sharpe_in_sample": ms_w,
}, index=returns.columns)
alloc.loc["return"] = [eq_r, inv_r, ms_r]
alloc.loc["vol"] = [eq_v, inv_v, ms_v]
alloc.loc["sharpe"] = [eq_s, inv_s, ms_s]
print(alloc.round(3))
"""),
        md("""## Efficient-frontier cloud

Each dot is one long-only random portfolio. The left edge of the cloud is the empirical frontier *on this sample*. The star is in-sample max Sharpe; the square is 1/N; the triangle is inverse-vol. If the star is far above the square, you are looking at estimation luck as much as at "optimization." """),
        code("""fig, ax = plt.subplots(figsize=(8.5, 5.2))
sc = ax.scatter(rand_v, rand_r, c=rand_s, s=8, cmap="viridis", alpha=0.45)
fig.colorbar(sc, ax=ax, label=f"Sharpe vs {rf:.0%} cash")
ax.scatter([eq_v], [eq_r], marker="s", s=80, color="#1a1a1a", label="equal weight", zorder=3)
ax.scatter([inv_v], [inv_r], marker="^", s=90, color="#2563eb", label="inverse vol", zorder=3)
ax.scatter([ms_v], [ms_r], marker="*", s=180, color="#be123c", label="max Sharpe (in-sample)", zorder=3)
ax.set_xlabel("Annualized volatility")
ax.set_ylabel("Annualized return")
ax.set_title("Long-only random portfolios — empirical frontier, this window only")
ax.legend(frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
plt.show()
"""),
        md("""## Equity curves and max drawdown

Convert each weight vector into a daily portfolio return, compound it, and measure the worst peak-to-trough. The in-sample max-Sharpe curve will often win the return race and still surprise you on drawdown. Costs, lot sizes and taxes are not in this picture — notebook 29 is where those go."""),
        code("""def equity(weights):
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    port = returns.values @ w
    curve = (1 + pd.Series(port, index=returns.index)).cumprod()
    dd = curve / curve.cummax() - 1
    return curve, float(dd.min()), pd.Series(port, index=returns.index)

curves = {}
print(f"{'rule':<24} {'end':>8} {'maxDD':>8} {'vol':>8} {'sharpe':>8}")
for name, weights in [("equal", eq_w), ("inv_vol", inv_w), ("max_sharpe_is", ms_w)]:
    curve, mdd, port = equity(weights)
    curves[name] = curve
    vol = port.std() * np.sqrt(252)
    sharpe = (port.mean() * 252 - rf) / vol
    print(f"{name:<24} {curve.iloc[-1]-1:>+7.1%} {mdd:>+7.1%} {vol:>7.1%} {sharpe:>8.2f}")

fig, ax = plt.subplots(figsize=(11, 4))
for name, curve in curves.items():
    ax.plot(curve.index, curve, lw=1.2, label=name)
ax.set_title("Growth of Rs.1 — same names, three weight rules, no costs")
ax.legend(frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
plt.show()
"""),
        md("""## How to read this without fooling yourself

- **1/N is the benchmark**, not the dumb option. DeMiguel, Garlappi and Uppal (2009) showed that a pile of "optimal" estimators lose to 1/N out of sample. If inverse-vol or a shrinking estimator cannot beat it after costs, keep 1/N.
- **Expected returns are the weak input.** Inverse-vol only needs volatilities, which are more stable than means. That is why it is the grown-up default when you do not have a real return forecast (and notebook 33 just showed you probably do not).
- **The red star is not a recommendation.** Re-run this cell in six months and it will move. PyPortfolioOpt's HRP and Black-Litterman exist because mean-variance on raw historical μ is fragile — use the [cookbook](https://github.com/PyPortfolioOpt/PyPortfolioOpt/tree/master/cookbook) when you want those estimators, and still score them on a later window.
- **Correlation clustering (notebook 32) first.** Five bank names in this basket are not five diversifiers; the frontier cannot invent independence the returns do not have.

Back to indicators: notebook 21's scenarios are single-name stories. A portfolio is how those stories are *sized* relative to each other."""),
    ]


def yfinance_drive_setup_cells():
    text = """!pip install -q yfinance prophet matplotlib

import os
from pathlib import Path
import yfinance as yf
import pandas as pd
import numpy as np

# Colab: attach Google Drive so forecasts, scorecards and charts survive
# the runtime. Local Jupyter: fall back to ./servloci-stock-lab in cwd.
def attach_store():
    try:
        from google.colab import drive  # type: ignore
        mount = Path("/content/drive")
        if not (mount / "MyDrive").exists():
            drive.mount("/content/drive")
        store = mount / "MyDrive" / "servloci-stock-lab"
        print("Google Drive attached:", store)
    except ImportError:
        store = Path("./servloci-stock-lab").resolve()
        print("Not Colab — writing artifacts locally:", store)
    store.mkdir(parents=True, exist_ok=True)
    return store

STORE = attach_store()
NSE_TICKER = "RELIANCE.NS"
US_TICKER = "AAPL"
INDEX_TICKER = "^NSEI"
TICKER = NSE_TICKER
PERIOD = "5y"
HORIZON_DAYS = 90  # calendar/business days for projectors
print("yfinance", yf.__version__)
print("artifact folder:", STORE)
"""
    return [md("## Setup — yfinance + Google Drive + Prophet"), code(text)]


def body_35_prophet_drive_lab():
    return [
        md("""## One ticker, three projectors, a folder that survives Colab

Kaggle "Prophet stock forecast" notebooks usually: `drive.mount`, `yfinance.download`, `Prophet().fit`, a fan chart, done. The fan looks like a view of the future. It is a **smoother with seasonality**, plus a confidence band that is not a trading interval.

This chapter keeps the useful Colab pattern — live `yfinance`, optional **Google Drive** persistence, **Prophet** as one projector — and puts it next to the things those notebooks skip:

- a **fundamental scorecard** (P/E, margins, leverage, growth, cash)
- a **technical scorecard** from the same 50-indicator engine as notebook 21
- **three projectors on one chart:** Prophet, the Street's analyst target (Yahoo), and a drift-and-vol cone
- a **holdout** so Prophet has to beat "price unchanged" before you screenshot the fan

Artifacts land in `MyDrive/servloci-stock-lab/<TICKER>/` on Colab, or `./servloci-stock-lab/` locally. Re-run the selector and everything overwrites in place.

Related reading (do not paste blindly): Facebook/Meta [Prophet docs](https://facebook.github.io/prophet/), typical Colab+Drive+yfinance+Prophet copies, notebook 26 (fundamentals), 21 (indicators), 33 (why price overlays lie)."""),
        code("!pip install -q pandas numpy matplotlib ipywidgets\n" + INDICATOR_ENGINE_SRC),
        md("""## Stock selector

Same Yahoo rules as the rest of the school: `RELIANCE.NS`, `AAPL`, `^NSEI`. Change the dropdown or type a custom symbol, then run the cells below."""),
        code("""from IPython.display import display, Markdown
import matplotlib.pyplot as plt
import json

STOCK_UNIVERSE = {
    "Nifty 50": "^NSEI",
    "Bank Nifty": "^NSEBANK",
    "Sensex": "^BSESN",
    "Reliance": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Infosys": "INFY.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "SBI": "SBIN.NS",
    "ITC": "ITC.NS",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "NVIDIA": "NVDA",
    "S&P 500": "^GSPC",
}

def load_ohlcv(ticker, period="5y"):
    raw = yf.download(
        ticker, period=period, interval="1d",
        auto_adjust=True, progress=False, multi_level_index=False,
    )
    if raw is None or raw.empty:
        raise ValueError(f"yfinance returned no rows for {ticker!r}")
    bars = raw.rename(columns={c: str(c).lower() for c in raw.columns})
    needed = ["open", "high", "low", "close", "volume"]
    missing = [c for c in needed if c not in bars.columns]
    if missing:
        raise ValueError(f"{ticker}: missing {missing}")
    bars = bars[needed].apply(pd.to_numeric, errors="coerce").dropna(how="any")
    if len(bars) < 120:
        raise ValueError(f"{ticker}: only {len(bars)} bars — need ~120+ for Prophet + indicators")
    return bars

def ticker_dir(ticker):
    safe = ticker.replace("^", "idx-").replace("/", "-")
    path = STORE / safe
    path.mkdir(parents=True, exist_ok=True)
    return path

TICKER = "RELIANCE.NS"
PERIOD = "5y"
try:
    import ipywidgets as W
    from ipywidgets import interactive_output
    stock = W.Dropdown(options=list(STOCK_UNIVERSE.items()), value=TICKER, description="Stock:")
    custom = W.Text(value="", placeholder="e.g. INFY.NS or AAPL", description="Custom:")
    period = W.ToggleButtons(options=["2y", "5y", "10y", "max"], value=PERIOD, description="Lookback:")

    def _pick(stock, custom, period):
        global TICKER, PERIOD, bars
        TICKER = (custom or "").strip() or stock
        PERIOD = period
        bars = load_ohlcv(TICKER, PERIOD)
        print(f"{TICKER}: {len(bars)} sessions {bars.index.min().date()} -> {bars.index.max().date()}")
        print("will write to", ticker_dir(TICKER))

    display(W.VBox([W.HBox([stock, period]), custom]),
            interactive_output(_pick, {"stock": stock, "custom": custom, "period": period}))
except ImportError:
    bars = load_ohlcv(TICKER, PERIOD)
    print("no ipywidgets — using", TICKER, len(bars), "bars")
"""),
        md("""### Fundamentals scorecard

These are Yahoo's latest snapshot fields — delayed, vendor-mapped, and sometimes missing for Indian names. A blank is "Yahoo did not return it," not "the company has no debt." None of this is a buy/sell rating."""),
        code("""def ensure_bars():
    global TICKER, PERIOD, bars
    if "bars" not in globals():
        TICKER = globals().get("TICKER", "RELIANCE.NS")
        PERIOD = globals().get("PERIOD", "5y")
        bars = load_ohlcv(TICKER, PERIOD)
    return bars

def fundamental_snapshot(ticker):
    info = yf.Ticker(ticker).info or {}
    keys = [
        "longName", "sector", "industry", "currency", "marketCap",
        "currentPrice", "previousClose", "fiftyTwoWeekLow", "fiftyTwoWeekHigh",
        "trailingPE", "forwardPE", "pegRatio", "priceToBook", "enterpriseToEbitda",
        "profitMargins", "operatingMargins", "returnOnEquity", "returnOnAssets",
        "debtToEquity", "currentRatio", "freeCashflow", "operatingCashflow",
        "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth",
        "dividendYield", "payoutRatio", "beta",
        "targetMeanPrice", "targetMedianPrice", "targetHighPrice", "targetLowPrice",
        "numberOfAnalystOpinions", "recommendationKey", "recommendationMean",
    ]
    snap = {k: info.get(k) for k in keys}
    snap["ticker"] = ticker
    return snap, info

bars = ensure_bars()
fund, raw_info = fundamental_snapshot(TICKER)
spot = float(bars["close"].iloc[-1])
fund["last_close"] = spot
display(pd.Series(fund).to_frame("value"))

def flag_fundamentals(s):
    rows = []
    def add(name, ok, detail):
        rows.append({"point": name, "ok": ok, "detail": detail})
    pe = s.get("trailingPE")
    add("PE is finite and not extreme (>0, <60)",
        pe is not None and 0 < float(pe) < 60,
        f"trailing PE={pe}")
    fpe = s.get("forwardPE")
    add("Forward PE available and below trailing (growth priced in, or just cheaper fwd)",
        fpe is not None and pe is not None and 0 < float(fpe) <= float(pe) * 1.05,
        f"forward PE={fpe}")
    margin = s.get("profitMargins")
    add("Profit margin positive",
        margin is not None and float(margin) > 0,
        f"profit margin={margin}")
    roe = s.get("returnOnEquity")
    add("ROE positive",
        roe is not None and float(roe) > 0,
        f"ROE={roe}")
    de = s.get("debtToEquity")
    add("Debt/equity reported and under 200",
        de is not None and 0 <= float(de) < 200,
        f"D/E={de}")
    growth = s.get("revenueGrowth")
    add("Revenue growth not deeply negative",
        growth is None or float(growth) > -0.15,
        f"revenue growth={growth}")
    fcf = s.get("freeCashflow")
    add("Free cash flow positive (when Yahoo reports it)",
        fcf is None or float(fcf) > 0,
        f"FCF={fcf}")
    lo, hi = s.get("fiftyTwoWeekLow"), s.get("fiftyTwoWeekHigh")
    if lo and hi and float(hi) > float(lo):
        loc = (spot - float(lo)) / (float(hi) - float(lo))
        add("Not pinned at the 52-week high (location < 0.98)",
            loc < 0.98, f"52w location={loc:.0%}")
    else:
        add("52-week range available", False, "Yahoo did not return 52w high/low")
    return pd.DataFrame(rows)

fund_flags = flag_fundamentals(fund)
print(f"\\n{TICKER} fundamental checklist  ({int(fund_flags.ok.sum())}/{len(fund_flags)} points true)")
display(fund_flags)
"""),
        md("""### Technical scorecard

Same engine as notebook 21. The "points" below are *descriptions of the last closed bar*, not entries. A close above SMA20 in a 10-ADX chop is not a trend."""),
        code("""bars = ensure_bars()
indicators = compute_top_50(bars)
last = indicators.iloc[-1]
close = bars["close"]
spot = float(close.iloc[-1])

tech = {
    "close": spot,
    "sma20": float(last["01_sma_20"]),
    "ema20": float(last["02_ema_20"]),
    "macd": float(last["08_macd"]),
    "macd_signal": float(last["09_macd_signal"]),
    "rsi14": float(last["14_rsi_14"]),
    "bb_upper": float(last["25_bollinger_upper"]),
    "bb_lower": float(last["26_bollinger_lower"]),
    "bb_bandwidth": float(last["27_bollinger_bandwidth"]),
    "atr14": float(last["28_atr_14"]),
    "hv20": float(last["36_historical_volatility"]),
    "adx14": float(last["37_adx_14"]),
    "plus_di": float(last["38_plus_di"]),
    "minus_di": float(last["39_minus_di"]),
    "mfi14": float(last["48_mfi_14"]),
}
display(pd.Series(tech).to_frame("value"))

tech_flags = pd.DataFrame([
    {"point": "Close above SMA20 (short-term average reclaim)",
     "ok": spot > tech["sma20"], "detail": f"close {spot:.2f} vs SMA {tech['sma20']:.2f}"},
    {"point": "EMA20 above SMA20 (rising-average regime)",
     "ok": tech["ema20"] > tech["sma20"], "detail": f"EMA {tech['ema20']:.2f} / SMA {tech['sma20']:.2f}"},
    {"point": "MACD above signal (short-term momentum confirmation)",
     "ok": tech["macd"] > tech["macd_signal"], "detail": f"MACD {tech['macd']:.3f} / sig {tech['macd_signal']:.3f}"},
    {"point": "RSI not overbought (>70)",
     "ok": tech["rsi14"] <= 70, "detail": f"RSI {tech['rsi14']:.1f}"},
    {"point": "RSI not oversold (<30)",
     "ok": tech["rsi14"] >= 30, "detail": f"RSI {tech['rsi14']:.1f}"},
    {"point": "Close inside Bollinger bands (not walking an extreme)",
     "ok": tech["bb_lower"] <= spot <= tech["bb_upper"],
     "detail": f"[{tech['bb_lower']:.2f}, {tech['bb_upper']:.2f}]"},
    {"point": "ADX >= 20 (something other than dead chop)",
     "ok": tech["adx14"] >= 20, "detail": f"ADX {tech['adx14']:.1f}"},
    {"point": "+DI above -DI (directional control, if any)",
     "ok": tech["plus_di"] > tech["minus_di"],
     "detail": f"+DI {tech['plus_di']:.1f} / -DI {tech['minus_di']:.1f}"},
    {"point": "MFI between 20 and 80 (volume-weighted oscillator not pinned)",
     "ok": 20 <= tech["mfi14"] <= 80, "detail": f"MFI {tech['mfi14']:.1f}"},
])
print(f"\\n{TICKER} technical checklist  ({int(tech_flags.ok.sum())}/{len(tech_flags)} points true)")
display(tech_flags)
"""),
        md("""## Projectors — Prophet, Street target, vol cone

Three different objects, often drawn as if they were one forecast:

1. **Prophet** (`yhat` ± interval) — decomposes the *price level* into trend + yearly seasonality. It will hug a drifting series and look "accurate" on a price chart for the same reason notebook 33's naive overlay does.
2. **Analyst target** — Yahoo's consensus `targetMeanPrice` (when present). A 12-month-ish Street number, not a path, and often stale.
3. **Drift-and-vol cone** — last close grown at the sample mean, with ±1σ / ±2σ bands from realized vol. This is a **distribution sketch**, not a prediction.

None of them is a trade. The holdout cell below is the only number that can embarrass Prophet."""),
        code("""from datetime import timedelta

def naive_dates(index):
    idx = pd.to_datetime(index)
    if getattr(idx, "tz", None) is not None:
        return idx.tz_convert("UTC").tz_localize(None)
    return idx

bars = ensure_bars()
close = bars["close"]
spot = float(close.iloc[-1])
horizon = int(globals().get("HORIZON_DAYS", 90))

# --- Prophet on the full sample (the pretty chart) ---
from prophet import Prophet

prophet_df = pd.DataFrame({
    "ds": naive_dates(close.index),
    "y": close.values,
})
model = Prophet(
    daily_seasonality=False,
    weekly_seasonality=False,
    yearly_seasonality=True,
    changepoint_prior_scale=0.05,
)
model.fit(prophet_df)
future = model.make_future_dataframe(periods=horizon, freq="B")
forecast = model.predict(future)
forecast_future = forecast[forecast["ds"] > prophet_df["ds"].max()].copy()
print(f"Prophet fitted on {len(prophet_df)} days; projecting {len(forecast_future)} business days")
print(forecast_future[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(3))

# --- Analyst projector ---
tgt_mean = fund.get("targetMeanPrice")
tgt_hi = fund.get("targetHighPrice")
tgt_lo = fund.get("targetLowPrice")
n_op = fund.get("numberOfAnalystOpinions")
print(f"analyst target mean={tgt_mean}  high={tgt_hi}  low={tgt_lo}  n={n_op}")

# --- Drift / vol cone ---
log_ret = np.log(close / close.shift(1)).dropna()
mu = float(log_ret.mean())
sig = float(log_ret.std())
steps = np.arange(1, horizon + 1)
cone_idx = pd.bdate_range(close.index[-1] + timedelta(days=1), periods=horizon)
drift = spot * np.exp(mu * steps)
cone = pd.DataFrame({
    "mid": drift,
    "lo1": spot * np.exp(mu * steps - sig * np.sqrt(steps)),
    "hi1": spot * np.exp(mu * steps + sig * np.sqrt(steps)),
    "lo2": spot * np.exp(mu * steps - 2 * sig * np.sqrt(steps)),
    "hi2": spot * np.exp(mu * steps + 2 * sig * np.sqrt(steps)),
}, index=cone_idx)
print(f"vol cone: daily mu={mu:.5f}, sigma={sig:.5f}, {horizon}d mid={cone['mid'].iloc[-1]:.2f}")
"""),
        md("""### Projector chart

Price + SMA20 + Bollinger, then the three projectors to the right of the last bar. If Prophet's fan and the vol cone disagree violently, believe neither — they encode different assumptions."""),
        code("""fig, axes = plt.subplots(2, 1, figsize=(11.5, 8.2), sharex=False,
                         gridspec_kw={"height_ratios": [2.4, 1]})
ax = axes[0]
hist = close.iloc[-min(len(close), 400):]
ax.plot(hist.index, hist.values, color="#1a1a1a", lw=1.15, label="Close")
ax.plot(indicators.index, indicators["01_sma_20"], color="#2563eb", lw=0.9, label="SMA20")
ax.fill_between(indicators.index, indicators["26_bollinger_lower"], indicators["25_bollinger_upper"],
                color="#2563eb", alpha=0.08, label="Bollinger")
ax.plot(forecast_future["ds"], forecast_future["yhat"], color="#7c3aed", lw=1.2, label="Prophet yhat")
ax.fill_between(forecast_future["ds"], forecast_future["yhat_lower"], forecast_future["yhat_upper"],
                color="#7c3aed", alpha=0.15, label="Prophet interval")
ax.plot(cone.index, cone["mid"], color="#0f766e", lw=1.0, ls="--", label="drift mid")
ax.fill_between(cone.index, cone["lo1"], cone["hi1"], color="#0f766e", alpha=0.12, label="vol ±1σ")
if tgt_mean:
    ax.axhline(float(tgt_mean), color="#be123c", lw=1.0, ls=":", label=f"analyst mean {float(tgt_mean):.1f}")
ax.set_title(f"{TICKER} — price, technicals, and three projectors")
ax.legend(loc="upper left", fontsize=7, frameon=False, ncol=2)
ax.grid(True, alpha=0.25)

axes[1].plot(indicators.index, indicators["14_rsi_14"], color="#0f766e", lw=1)
axes[1].axhline(70, color="#b45309", ls="--", lw=0.8)
axes[1].axhline(30, color="#b45309", ls="--", lw=0.8)
axes[1].set_ylim(0, 100)
axes[1].set_ylabel("RSI 14")
axes[1].grid(True, alpha=0.25)
fig.tight_layout()
projector_png = ticker_dir(TICKER) / "projector.png"
fig.savefig(projector_png, dpi=140, bbox_inches="tight")
plt.show()
print("saved", projector_png)

fig2 = model.plot_components(forecast)
fig2.set_size_inches(11, 6)
components_png = ticker_dir(TICKER) / "prophet_components.png"
fig2.savefig(components_png, dpi=120, bbox_inches="tight")
plt.show()
print("saved", components_png)
"""),
        md("""### Holdout — Prophet vs naive on the last 90 sessions

Fit on everything *before* the last 90 bars, project those 90, score **prices and returns**. If Prophet's price MAE is only a hair under naive, the fan chart is a smoother. Notebook 33 is the longer version of this argument."""),
        code("""hold = min(90, max(40, len(close) // 6))
train_close = close.iloc[:-hold]
test_close = close.iloc[-hold:]
train_df = pd.DataFrame({
    "ds": naive_dates(train_close.index),
    "y": train_close.values,
})
hold_model = Prophet(daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=True)
hold_model.fit(train_df)
hold_future = hold_model.make_future_dataframe(periods=hold, freq="B")
hold_fc = hold_model.predict(hold_future)
pred = hold_fc.set_index("ds")["yhat"].reindex(naive_dates(test_close.index))
aligned = pd.DataFrame({"actual": test_close.values, "prophet": pred.values}, index=test_close.index).dropna()
naive = pd.Series(float(train_close.iloc[-1]), index=aligned.index)
mae_p = float(np.mean(np.abs(aligned["actual"] - aligned["prophet"])))
mae_n = float(np.mean(np.abs(aligned["actual"] - naive)))
# return-space: next-day change implied by the path vs actual change
act_ret = aligned["actual"].pct_change(fill_method=None).dropna()
pr_ret = aligned["prophet"].pct_change(fill_method=None).reindex(act_ret.index)
naive_ret = pd.Series(0.0, index=act_ret.index)
print(f"holdout {aligned.index.min().date()} -> {aligned.index.max().date()}  ({len(aligned)} sessions)")
print(f"price MAE  prophet={mae_p:.3f}  naive(last train close)={mae_n:.3f}")
print(f"return MAE prophet={float(np.mean(np.abs(act_ret - pr_ret))):.5f}  naive(0)={float(np.mean(np.abs(act_ret))):.5f}")
print("If return MAE is not clearly better than naive, do not ship the fan as a forecast.")
"""),
        md("""## Write the lab folder (Drive or local)

Every re-run overwrites the ticker's folder. Take the PNG and the scorecard into a note; do not treat `forecast.csv` as an order blotter."""),
        code("""out = ticker_dir(TICKER)
bars.to_csv(out / "ohlcv.csv")
indicators.to_csv(out / "indicators.csv")
forecast.to_csv(out / "prophet_forecast.csv", index=False)
cone.to_csv(out / "vol_cone.csv")
pd.Series(fund).to_json(out / "fundamentals.json", indent=2)
fund_flags.to_csv(out / "fundamentals_checklist.csv", index=False)
tech_flags.to_csv(out / "technicals_checklist.csv", index=False)

score = [
    f"# {TICKER} lab scorecard",
    f"as_of: {bars.index[-1].date()}  close: {spot:.4f}  store: {out}",
    "",
    "## Fundamentals",
    fund_flags.to_string(index=False),
    "",
    "## Technicals (last closed bar)",
    tech_flags.to_string(index=False),
    "",
    "## Projectors",
    f"Prophet {horizon}d yhat: {float(forecast_future['yhat'].iloc[-1]):.2f} "
    f"[{float(forecast_future['yhat_lower'].iloc[-1]):.2f}, {float(forecast_future['yhat_upper'].iloc[-1]):.2f}]",
    f"Vol-cone mid: {float(cone['mid'].iloc[-1]):.2f}  ±1σ "
    f"[{float(cone['lo1'].iloc[-1]):.2f}, {float(cone['hi1'].iloc[-1]):.2f}]",
    f"Analyst mean target: {tgt_mean}  (n={n_op})",
    f"Holdout price MAE prophet={mae_p:.3f} vs naive={mae_n:.3f}",
    "",
    "Educational only. Projectors are not orders.",
]
(out / "SCORECARD.md").write_text("\\n".join(score))
print("wrote", out)
print("\\n".join(sorted(p.name for p in out.iterdir())))
display(Markdown((out / "SCORECARD.md").read_text()))
"""),
        md("""## How to use this without fooling yourself

- **Drive is a filing cabinet.** It does not make Prophet more true. It just means the PNG is still there after Colab disconnects.
- **Fundamentals flags are existence checks**, not a quality compounder screen. "D/E under 200" is a sanity bound; sector norms differ.
- **Technical flags describe one bar.** Combine a trend read with a volatility or ADX filter before you even paper-trade (notebooks 21 and 23).
- **Three projectors should not be averaged into a "fair price."** They answer different questions. If you need a forecast research design, start from notebook 33's return-space naive baseline and notebook 29's costs.

Next: take a name that *fails* several fundamental flags and run notebook 21's scenario board on it — the indicators will still print numbers."""),
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
    {"filename": "20_indian_broker_api_landscape.ipynb", "title": "Indian Broker API Landscape", "subtitle": "Reviewed first-party API catalog, integration surface, static-IP concerns and selection checklist.", "body": body_20_broker_api_landscape},
    {"filename": "21_top_50_technical_indicators.ipynb", "title": "Top 50 Technical Indicators", "subtitle": "Pick a live ticker with the stock selector and compute 50 trend, momentum, volatility, directional and volume indicators from yfinance — no TA library.", "body": body_21_top_50_indicators, "setup": yfinance_setup_cells},
    {"filename": "22_broker_data_indicator_pipeline.ipynb", "title": "Broker Data to Indicator Pipeline", "subtitle": "Normalize broker OHLCV, compute all 50 indicators, and keep reads separate from routed order calls.", "body": body_22_broker_indicator_pipeline},
    {"filename": "23_alerts_and_servloci_dispatch.ipynb", "title": "Alerts and ServLoci Dispatch", "subtitle": "Generate de-duplicated alerts and pass reviewed intents to a dry-run ServLoci order boundary.", "body": body_23_alerts_and_servloci},
    {"filename": "24_reading_the_market_with_yfinance.ipynb", "title": "Reading the Market with yfinance", "subtitle": "Pull real NSE, BSE and US data with no broker account — OHLCV, adjusted close, dividends and splits explained.", "body": body_24_reading_the_market, "setup": yfinance_setup_cells},
    {"filename": "25_returns_volatility_and_risk_metrics.ipynb", "title": "Returns, Volatility & the Numbers Courses Skip", "subtitle": "Daily and log returns, annualized volatility, Sharpe, Sortino and max drawdown computed on real Nifty and S&P history.", "body": body_25_returns_and_risk, "setup": yfinance_setup_cells},
    {"filename": "26_fundamental_analysis_with_yfinance.ipynb", "title": "Fundamental Analysis with Real Filings", "subtitle": "P/E, market cap, debt/equity and revenue growth pulled live via yfinance — Reliance vs Apple, side by side.", "body": body_26_fundamental_analysis, "setup": yfinance_setup_cells},
    {"filename": "27_technical_indicators_tested_honestly.ipynb", "title": "Technical Indicators, Tested Honestly", "subtitle": "Run the 50-indicator engine on real data and measure which signals actually correlate with forward returns.", "body": body_27_indicators_tested_honestly, "setup": yfinance_setup_cells},
    {"filename": "28_options_priced_against_reality.ipynb", "title": "Options, Priced Against Reality", "subtitle": "Black-Scholes and the Greeks anchored to a real fetched spot price, not a made-up number.", "body": body_28_options_against_reality, "setup": yfinance_setup_cells},
    {"filename": "29_backtesting_without_fooling_yourself.ipynb", "title": "Backtesting Without Fooling Yourself", "subtitle": "Lookahead bias, overfitting and real transaction costs — demonstrated, not just warned about.", "body": body_29_backtesting_honestly, "setup": yfinance_setup_cells},
    {"filename": "30_position_sizing_and_trading_psychology.ipynb", "title": "Position Sizing, Risk of Ruin & Trading Psychology", "subtitle": "Monte Carlo equity curves on real volatility, and the quantified cost of a psychology-driven mistake.", "body": body_30_position_sizing_psychology, "setup": yfinance_setup_cells},
    {"filename": "31_capstone_stock_market_school.ipynb", "title": "Capstone: Build Your Own Strategy End to End", "subtitle": "Fundamentals filter + tested indicator + honest backtest + risk-managed sizing, real tickers start to finish.", "body": body_31_school_capstone, "setup": yfinance_setup_cells},
    {"filename": "32_stock_correlation_and_pairs.ipynb", "title": "Stock Correlation, Clusters and Pairs", "subtitle": "Live-basket correlation heatmap, rolling correlation vs Nifty, and why a tight pair is not a hedge — the useful part of the Kaggle market-analysis notebooks.", "body": body_32_correlation_and_pairs, "setup": yfinance_setup_cells},
    {"filename": "33_return_prediction_baselines.ipynb", "title": "Return Prediction Baselines (Beat Naive First)", "subtitle": "Time-ordered linear and forest forecasts vs a zero-return naive baseline — the honest rewrite of the copied LSTM price-prediction notebooks.", "body": body_33_prediction_baselines, "setup": yfinance_setup_cells},
    {"filename": "34_portfolio_analytics.ipynb", "title": "Portfolio Analytics: Weights, Frontier, Drawdown", "subtitle": "Equal-weight vs inverse-vol vs in-sample max Sharpe on a live NSE basket, Monte Carlo frontier, equity curves — PyPortfolioOpt-style, no extra optimiser.", "body": body_34_portfolio_analytics, "setup": yfinance_setup_cells},
    {"filename": "35_prophet_drive_fundamentals_projectors.ipynb", "title": "Prophet, Drive Lab & Three Projectors", "subtitle": "yfinance + Google Drive persistence: fundamental and technical scorecards, Prophet fan, analyst target and a vol cone — with a holdout that has to beat naive.", "body": body_35_prophet_drive_lab, "setup": yfinance_drive_setup_cells},
]

NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "name": "python3"},
    "language_info": {"name": "python"},
    "colab": {"provenance": [], "name": None},
}


def build_notebook(idx, entry):
    setup_fn = entry.get("setup", setup_cells)
    cells = (
        header_cells(idx, entry["filename"], entry["title"], entry["subtitle"])
        + setup_fn()
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

    standalone = build_colab_dhan_notebook()
    standalone_path = os.path.join(OUT_DIR, "colab_dhan_trading_static_ip.ipynb")
    with open(standalone_path, "w") as f:
        json.dump(standalone, f, indent=1)
        f.write("\n")
    print("wrote", os.path.basename(standalone_path))


if __name__ == "__main__":
    main()
