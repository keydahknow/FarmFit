"""Convert GIT_SHEET.md to GIT_SHEET.pdf (requires markdown, playwright)."""

from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "GIT_SHEET.md"
PDF_PATH = ROOT / "GIT_SHEET.pdf"
HTML_PATH = ROOT / "scripts" / "_git_sheet_print.html"

STYLE = """
@page { margin: 18mm; }
body {
  font-family: system-ui, Segoe UI, Helvetica, Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.45;
  color: #143122;
  max-width: 100%;
}
h1 { font-size: 20pt; border-bottom: 2px solid #c8e6c0; padding-bottom: 6pt; }
h2 { font-size: 14pt; margin-top: 1.2em; color: #1a4d3a; }
h3 { font-size: 12pt; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f4f4f4; padding: 1px 4px; }
pre {
  font-family: Consolas, monospace;
  font-size: 8.5pt;
  background: #f4f4f4;
  padding: 10pt;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}
table { border-collapse: collapse; width: 100%; margin: 10pt 0; font-size: 10pt; }
th, td { border: 1px solid #ccc; padding: 6pt 8pt; vertical-align: top; }
th { background: #eef7e9; text-align: left; }
"""


def main() -> None:
    text = MD_PATH.read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{STYLE}</style></head>
<body>{body}</body></html>"""
    HTML_PATH.write_text(html, encoding="utf-8")

    file_url = HTML_PATH.resolve().as_uri()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.pdf(
            path=str(PDF_PATH),
            format="Letter",
            margin={"top": "18mm", "right": "18mm", "bottom": "18mm", "left": "18mm"},
            print_background=True,
        )
        browser.close()

    print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    main()
