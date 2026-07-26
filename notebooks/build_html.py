#!/usr/bin/env python3
"""Render every notebook to static HTML for comm.servloci.in/notebooks/.

Output goes to web/public/notebooks/ so Nuxt's `generate` step copies it
straight into the static build (same mechanism as public/robots.txt) and
it ends up embedded in the Go binary via `//go:embed all:ui/dist`.

Run after generate_notebooks.py, or standalone against existing .ipynb
files: `python3 notebooks/build_html.py`.
"""
import os

from nbconvert import HTMLExporter
from traitlets.config import Config

from generate_notebooks import NOTEBOOKS, GITHUB_REPO, BRANCH

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


def render_notebook(entry):
    exporter = HTMLExporter(config=Config())
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    src = os.path.join(HERE, entry["filename"])
    body, _ = exporter.from_filename(src)
    return body


def build():
    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    for entry in NOTEBOOKS:
        html_name = entry["filename"].replace(".ipynb", ".html")
        html = render_notebook(entry)
        with open(os.path.join(OUT_DIR, html_name), "w") as f:
            f.write(html)
        rows.append((entry["filename"], html_name, entry["title"], entry["subtitle"]))
        print(f"wrote {html_name}")

    index_items = []
    for filename, html_name, title, subtitle in rows:
        colab_url = f"https://colab.research.google.com/github/{GITHUB_REPO}/blob/{BRANCH}/notebooks/{filename}"
        github_url = f"https://github.com/{GITHUB_REPO}/blob/{BRANCH}/notebooks/{filename}"
        index_items.append(f"""    <li>
      <a href="/notebooks/{html_name}">{title}</a>
      <span class="sub">{subtitle}</span>
      <span class="badges">
        <a href="{colab_url}" target="_blank" rel="noopener">Open in Colab</a>
        <a href="{github_url}" target="_blank" rel="noopener">View source</a>
      </span>
    </li>""")

    index_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ServLoci Colab Notebook Series</title>
<style>{INDEX_CSS}</style>
</head>
<body>
  <h1>ServLoci Colab Notebook Series</h1>
  <p class="lead">20 free notebooks covering the ServLoci SDK, broker auth, options pricing,
  strategy templates, backtesting, risk sizing, and a capstone algo bot. Read the rendered
  output below, or open any of them in Colab and run it yourself.</p>
  <ol>
{chr(10).join(index_items)}
  </ol>
  <footer>
    Every notebook fetches a dedicated static IPv6 + SOCKS5 proxy from
    <a href="https://comm.servloci.in">comm.servloci.in</a> in its setup cell —
    see <a href="https://comm.servloci.in/docs">the docs</a> for how broker APIs use it.
  </footer>
</body>
</html>
"""
    with open(os.path.join(OUT_DIR, "index.html"), "w") as f:
        f.write(index_html)
    print(f"wrote index.html ({len(rows)} notebooks)")


if __name__ == "__main__":
    build()
