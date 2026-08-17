#!/usr/bin/env python3
"""Render every notebook to static HTML for comm.servloci.in/notebooks/.

Output goes to web/public/notebooks/ so Nuxt's `generate` step copies it
straight into the static build (same mechanism as public/robots.txt) and
it ends up embedded in the Go binary via `//go:embed all:ui/dist`.

Run after generate_notebooks.py, or standalone against existing .ipynb
files: `python3 notebooks/build_html.py`.
"""
import html
import os
import re

from nbconvert import HTMLExporter
from traitlets.config import Config

from generate_notebooks import NOTEBOOKS, GITHUB_REPO, BRANCH

STANDALONE_NOTEBOOKS = [
    {
        "filename": "colab_dhan_trading_static_ip.ipynb",
        "title": "Complete Colab Quickstart: Dhan + Static IP",
        "subtitle": "One-token setup, Colab Secrets, IPv6 verification, and DhanHQ 2.2 read-only test.",
    },
]

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "web", "public", "notebooks")

INDEX_CSS = """
body{font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:840px;
margin:0 auto;padding:40px 20px;color:#1a1a1a;background:#fff}
h1{font-size:28px;margin-bottom:4px}
p.lead{color:#555;margin-top:0}
ol{padding-left:20px}
li{margin-bottom:14px}
a{color:#2563eb;text-decoration:none}
a:hover{text-decoration:underline}
.sub{color:#666;font-size:14px;display:block}
.badges{margin-top:2px}
.badges a{margin-right:10px;font-size:13px}
footer{margin-top:40px;color:#666;font-size:14px}
"""

# Category label per filename-number prefix, for the sidepanel grouping in
# the reader UI. Falls back to "More" for anything not listed.
CATEGORIES = [
    ("Setup", (0, 1)),
    ("Broker auth", (2, 5)),
    ("Options math", (6, 7)),
    ("Strategy templates", (8, 10)),
    ("Live data", (11, 12)),
    ("Backtesting", (13, 14)),
    ("Risk & execution", (15, 19)),
    ("Broker APIs & indicators", (20, 23)),
    ("Stock Market School (yfinance, no signup)", (24, 34)),
]


def category_for(index):
    for label, (lo, hi) in CATEGORIES:
        if lo <= index <= hi:
            return label
    return "More"


READER_CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#1a1a1a}
.reader{display:flex;height:100vh}
.sidepanel{width:300px;flex:none;border-right:1px solid #e5e7eb;overflow-y:auto;
background:#fafafa;padding:16px 0}
.sidepanel h1{font-size:16px;margin:0 16px 2px}
.sidepanel .lead{font-size:12.5px;color:#666;margin:0 16px 16px}
.sidepanel .back{display:block;margin:0 16px 12px;font-size:12.5px;color:#2563eb;text-decoration:none}
.learning{margin:0 12px 16px;padding:12px;border:1px solid #dfe7e2;border-radius:10px;background:#f5f8f6}
.learning h2{margin:0 0 7px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#2b5f4e}
.learning a{display:block;color:#244e40;text-decoration:none;font-size:12.5px;margin:5px 0}
.learning a:hover{text-decoration:underline}
.learning span{color:#737973;font-size:11.5px;display:block}
.group h2{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#888;
margin:16px 16px 4px;font-weight:600}
.nb-link{display:block;padding:8px 16px;color:#1a1a1a;text-decoration:none;font-size:13.5px;
border-left:3px solid transparent;cursor:pointer}
.nb-link:hover{background:#f0f0f0}
.nb-link.active{background:#eef2ff;border-left-color:#2563eb;color:#2563eb;font-weight:600}
.nb-link .n{color:#999;font-variant-numeric:tabular-nums;margin-right:6px}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.toolbar{flex:none;display:flex;align-items:center;gap:10px;padding:10px 16px;
border-bottom:1px solid #e5e7eb;background:#fff}
.toolbar h2{font-size:14px;margin:0;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;
white-space:nowrap}
.toolbar a{font-size:12.5px;color:#2563eb;text-decoration:none;white-space:nowrap}
.toolbar a:hover{text-decoration:underline}
iframe{flex:1;border:0;width:100%}
@media (max-width:760px){
  .reader{flex-direction:column;height:auto}
  .sidepanel{width:auto;max-height:40vh;border-right:0;border-bottom:1px solid #e5e7eb}
  iframe{min-height:60vh}
}
"""


def render_notebook(entry):
    exporter = HTMLExporter(config=Config())
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    src = os.path.join(HERE, entry["filename"])
    body, _ = exporter.from_filename(src)
    html_name = entry["filename"].replace(".ipynb", ".html")
    title = html.escape(f'{entry["title"]} · ServLoci notebook')
    description = html.escape(entry["subtitle"], quote=True)
    canonical = f"https://comm.servloci.in/notebooks/{html_name}"
    head = (
        f"<title>{title}</title>\n"
        f'<meta name="description" content="{description}">\n'
        '<meta name="robots" content="index, follow">\n'
        f'<link rel="canonical" href="{canonical}">\n'
        f'<meta property="og:title" content="{title}">\n'
        f'<meta property="og:description" content="{description}">\n'
        f'<meta property="og:url" content="{canonical}">'
    )
    body = re.sub(r"<title>.*?</title>", head, body, count=1, flags=re.DOTALL)
    return body


def build():
    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    for entry in NOTEBOOKS + STANDALONE_NOTEBOOKS:
        html_name = entry["filename"].replace(".ipynb", ".html")
        html = render_notebook(entry)
        with open(os.path.join(OUT_DIR, html_name), "w") as f:
            f.write(html)
        rows.append((entry["filename"], html_name, entry["title"], entry["subtitle"]))
        print(f"wrote {html_name}")

    # Group into sidebar sections, in NOTEBOOKS order.
    groups = {}
    group_order = []
    for i, (filename, html_name, title, subtitle) in enumerate(rows):
        label = category_for(i)
        if label not in groups:
            groups[label] = []
            group_order.append(label)
        colab_url = f"https://colab.research.google.com/github/{GITHUB_REPO}/blob/{BRANCH}/notebooks/{filename}"
        github_url = f"https://github.com/{GITHUB_REPO}/blob/{BRANCH}/notebooks/{filename}"
        groups[label].append({
            "n": f"{i:02d}", "html_name": html_name, "title": title,
            "subtitle": subtitle, "colab": colab_url, "github": github_url,
        })

    sidebar_sections = []
    for label in group_order:
        items = []
        for it in groups[label]:
            items.append(
                f'      <a class="nb-link" href="/notebooks/{it["html_name"]}" '
                f'data-html="{it["html_name"]}" data-title="{it["title"]}" '
                f'data-colab="{it["colab"]}" data-github="{it["github"]}">'
                f'<span class="n">{it["n"]}</span>{it["title"]}</a>'
            )
        sidebar_sections.append(
            f'    <div class="group">\n      <h2>{label}</h2>\n' + "\n".join(items) + "\n    </div>"
        )

    first = rows[0]
    first_html_name = first[1]

    index_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ServLoci Colab Notebook Series</title>
<meta name="description" content="A 35-part stock market and algo-trading course: real yfinance data and simulation, options math, 50 technical indicators, correlation, prediction baselines, portfolio analytics, backtesting, risk management and Indian broker APIs.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://comm.servloci.in/notebooks/">
<style>{READER_CSS}</style>
</head>
<body>
  <div class="reader">
    <nav class="sidepanel">
      <a class="back" href="https://comm.servloci.in">&larr; comm.servloci.in</a>
      <h1>Notebook series</h1>
      <p class="lead">35-part course + complete Dhan quickstart. Pick one — it loads on the right.</p>
      <div class="learning">
        <h2>Start here — no signup needed</h2>
        <a href="/notebooks/24_reading_the_market_with_yfinance.html">1. Read real market data<span>yfinance, no broker account</span></a>
        <a href="/notebooks/25_returns_volatility_and_risk_metrics.html">2. Returns, vol, Sharpe, drawdown<span>The numbers courses skip</span></a>
        <a href="/notebooks/29_backtesting_without_fooling_yourself.html">3. Backtest without fooling yourself<span>Lookahead bias &amp; real costs</span></a>
        <a href="/notebooks/31_capstone_stock_market_school.html">4. Capstone: your own strategy<span>Real tickers, start to finish</span></a>
        <a href="/notebooks/32_stock_correlation_and_pairs.html">5. Correlation and pairs<span>Heatmap, rolling corr, not a hedge</span></a>
        <a href="/notebooks/33_return_prediction_baselines.html">6. Prediction vs naive<span>Beat zero-return first</span></a>
        <a href="/notebooks/34_portfolio_analytics.html">7. Portfolio analytics<span>Weights, frontier, drawdown</span></a>
      </div>
      <div class="learning">
        <h2>Broker-integration learning path</h2>
        <a href="/notebooks/20_indian_broker_api_landscape.html">1. Compare broker APIs<span>18 first-party API sources</span></a>
        <a href="/notebooks/21_top_50_technical_indicators.html">2. Compute 50 indicators<span>One dependency-light engine</span></a>
        <a href="/notebooks/22_broker_data_indicator_pipeline.html">3. Connect broker candles<span>Normalize once, reuse everywhere</span></a>
        <a href="/notebooks/23_alerts_and_servloci_dispatch.html">4. Alert safely<span>De-duplicate, risk-check, dry-run</span></a>
      </div>
{chr(10).join(sidebar_sections)}
    </nav>
    <div class="main">
      <div class="toolbar">
        <h2 id="nb-title">{first[2]}</h2>
        <a id="nb-colab" target="_blank" rel="noopener">Open in Colab</a>
        <a id="nb-github" target="_blank" rel="noopener">View source</a>
        <a id="nb-standalone" target="_blank" rel="noopener">Open full page</a>
      </div>
      <iframe id="nb-frame" src="/notebooks/{first_html_name}" title="Notebook preview"></iframe>
    </div>
  </div>
  <script>
    var frame = document.getElementById('nb-frame');
    var title = document.getElementById('nb-title');
    var colab = document.getElementById('nb-colab');
    var github = document.getElementById('nb-github');
    var standalone = document.getElementById('nb-standalone');
    var links = document.querySelectorAll('.nb-link');
    function select(link, push) {{
      links.forEach(function(l) {{ l.classList.remove('active'); }});
      link.classList.add('active');
      var html = link.getAttribute('data-html');
      frame.src = '/notebooks/' + html;
      title.textContent = link.getAttribute('data-title');
      colab.href = link.getAttribute('data-colab');
      github.href = link.getAttribute('data-github');
      standalone.href = '/notebooks/' + html;
      if (push) history.replaceState(null, '', '#' + html.replace('.html', ''));
    }}
    links.forEach(function(link) {{
      link.addEventListener('click', function(e) {{
        e.preventDefault();
        select(link, true);
      }});
    }});
    var initial = links[0];
    if (location.hash) {{
      var wanted = location.hash.slice(1) + '.html';
      var match = Array.prototype.find.call(links, function(l) {{
        return l.getAttribute('data-html') === wanted;
      }});
      if (match) initial = match;
    }}
    select(initial, false);
  </script>
</body>
</html>
"""
    with open(os.path.join(OUT_DIR, "index.html"), "w") as f:
        f.write(index_html)
    print(f"wrote index.html ({len(rows)} notebooks, sidepanel reader)")


if __name__ == "__main__":
    build()
