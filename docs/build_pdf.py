"""Render CONCEPTS.md to CONCEPTS.pdf.

Not part of the tracklab application — a standalone tool with its own
venv (see the regenerate instructions at the top of CONCEPTS.md), kept
out of backend/requirements.txt so the app's dependency list stays
about the app, not about producing a PDF from documentation.
"""

from pathlib import Path

import markdown
from xhtml2pdf import pisa

DOCS_DIR = Path(__file__).parent
SOURCE = DOCS_DIR / "CONCEPTS.md"
OUTPUT = DOCS_DIR / "CONCEPTS.pdf"

CSS = """
@page {
    size: A4;
    margin: 2.2cm 2cm;
}
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 10.5pt;
    line-height: 1.5;
    color: #1a1a1a;
}
h1 {
    font-size: 20pt;
    color: #1b2a4a;
    border-bottom: 2px solid #1b2a4a;
    padding-bottom: 6px;
    margin-top: 0;
}
h2 {
    font-size: 15pt;
    color: #1b2a4a;
    margin-top: 26px;
    padding-top: 10px;
    border-top: 1px solid #ccc;
}
h3 {
    font-size: 12pt;
    color: #2c3e5c;
    margin-top: 18px;
}
code {
    font-family: "Courier New", monospace;
    font-size: 9.5pt;
    background-color: #f0f0f0;
    padding: 1px 3px;
}
pre {
    font-family: "Courier New", monospace;
    font-size: 9pt;
    background-color: #f5f5f5;
    padding: 8px 10px;
    border-left: 3px solid #888;
    white-space: pre-wrap;
}
pre code {
    background-color: transparent;
    padding: 0;
}
strong {
    color: #1b2a4a;
}
a {
    color: #1a5fb4;
    text-decoration: underline;
}
h3 + p, h2 + p {
    margin-top: 4px;
}
hr {
    border: none;
    border-top: 1px solid #bbb;
    margin: 20px 0;
}
ul, ol {
    margin-left: 4px;
}
"""


def build() -> None:
    md_text = SOURCE.read_text(encoding="utf-8")
    body_html = markdown.markdown(
        md_text, extensions=["fenced_code", "tables", "sane_lists"]
    )
    full_html = f"<html><head><style>{CSS}</style></head><body>{body_html}</body></html>"

    with open(OUTPUT, "wb") as out:
        result = pisa.CreatePDF(full_html, dest=out)

    if result.err:
        raise RuntimeError(f"PDF generation failed with {result.err} error(s)")

    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
