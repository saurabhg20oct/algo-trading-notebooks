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
        md(f"That's the core workflow. Recap: static IP (00) → SDK (01) → broker auth (02-05) → options math (06-10) → live data (11-12) → backtesting (13-14) → risk + execution (15-19). Continue with the broker API and indicator learning path in notebooks 20-23.\n\nKeep building at [{SITE}/tools/strategy-builder]({SITE}/tools/strategy-builder), or grab your own static IP at [{SITE}/register]({SITE}/register)."),
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
        code("!pip install -q pandas numpy matplotlib\n" + INDICATOR_ENGINE_SRC),
        md("## Run all 50 on reproducible demo OHLCV"),
        code("""rng = np.random.default_rng(7)
n = 320
close = pd.Series(22000 + rng.normal(0, 70, n).cumsum())
demo = pd.DataFrame({
    "open": close.shift(1).fillna(close.iloc[0]),
    "high": close + rng.uniform(10, 90, n),
    "low": close - rng.uniform(10, 90, n),
    "close": close,
    "volume": rng.integers(100_000, 900_000, n),
}, index=pd.date_range("2025-01-01", periods=n, freq="B"))

indicators = compute_top_50(demo)
print("indicator count:", indicators.shape[1])
display(indicators.tail(5).T)
assert indicators.shape[1] == 50
"""),
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
        code("!pip install -q pandas numpy requests\n" + INDICATOR_ENGINE_SRC),
        code("""def normalize_ohlcv(records, mapping):
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
        md("## Optional ServLoci order boundary (dry-run by default)"),
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
    {"filename": "21_top_50_technical_indicators.ipynb", "title": "Top 50 Technical Indicators", "subtitle": "Compute 50 trend, momentum, volatility, directional and volume indicators without a TA dependency.", "body": body_21_top_50_indicators},
    {"filename": "22_broker_data_indicator_pipeline.ipynb", "title": "Broker Data to Indicator Pipeline", "subtitle": "Normalize broker OHLCV, compute all 50 indicators, and keep reads separate from routed order calls.", "body": body_22_broker_indicator_pipeline},
    {"filename": "23_alerts_and_servloci_dispatch.ipynb", "title": "Alerts and ServLoci Dispatch", "subtitle": "Generate de-duplicated alerts and pass reviewed intents to a dry-run ServLoci order boundary.", "body": body_23_alerts_and_servloci},
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

    standalone = build_colab_dhan_notebook()
    standalone_path = os.path.join(OUT_DIR, "colab_dhan_trading_static_ip.ipynb")
    with open(standalone_path, "w") as f:
        json.dump(standalone, f, indent=1)
        f.write("\n")
    print("wrote", os.path.basename(standalone_path))


if __name__ == "__main__":
    main()
