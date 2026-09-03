"""Render CONCEPTS.md and CODE_GUIDE.md to PDF.

Not part of the tracklab application — a standalone tool with its own
venv (see the regenerate instructions at the top of CONCEPTS.md), kept
out of backend/requirements.txt so the app's dependency list stays
about the app, not about producing a PDF from documentation.

Cross-file links between the two documents (e.g. CODE_GUIDE.md linking
to CONCEPTS.md#some-anchor) work when reading the .md files directly
(GitHub, an editor) but won't be clickable within a standalone PDF,
since each PDF is rendered independently -- a known, accepted
limitation. The .md files are the primary reading format; the PDFs are
an offline convenience.
"""

from pathlib import Path

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from pygments.formatters import HtmlFormatter
from xhtml2pdf import pisa

DOCS_DIR = Path(__file__).parent
DOCUMENTS = [
    (DOCS_DIR / "CONCEPTS.md", DOCS_DIR / "CONCEPTS.pdf"),
    (DOCS_DIR / "CODE_GUIDE.md", DOCS_DIR / "CODE_GUIDE.pdf"),
]

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
    font-family: "Menlo", "Courier New", monospace;
    font-size: 8.5pt;
    line-height: 1.35;
    white-space: pre;
    background-color: #f6f8fa;
    padding: 10px 12px;
    border: 1px solid #d8dee4;
    border-radius: 3px;
}
pre code {
    background-color: transparent;
    padding: 0;
    white-space: pre;
}
.codehilite {
    background-color: #f6f8fa;
    border: 1px solid #d8dee4;
    border-radius: 3px;
    padding: 10px 12px;
    margin: 10px 0;
    overflow-x: auto;
}
.codehilite pre {
    border: none;
    padding: 0;
    margin: 0;
    background-color: transparent;
}
/* Inline line numbers (codehilite linenums='inline'): dim and
   right-padded, reading like a real editor's gutter rather than part
   of the code itself. */
.codehilite .linenos {
    color: #99a1a8;
    padding-right: 12px;
    -webkit-user-select: none;
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

# Pygments' own generated CSS for syntax token colours (keywords, strings,
# comments, decorators, ...) -- generated at build time rather than
# hand-copied, so it can never silently drift from the Pygments version
# actually installed.
PYGMENTS_CSS = HtmlFormatter(style="default", cssclass="codehilite").get_style_defs()


def _codehilite_extension() -> CodeHiliteExtension:
    # Built directly, not via markdown.markdown()'s extension_configs,
    # because that path coerces every config value through a strict
    # bool parser -- which rejects 'inline' even though Pygments' own
    # HtmlFormatter (what codehilite delegates 'linenums' to) accepts
    # it. Setting the config dict directly sidesteps that validation.
    ext = CodeHiliteExtension(guess_lang=False, css_class="codehilite")
    ext.config["linenums"][0] = "inline"
    return ext


def build_one(source: Path, output: Path) -> None:
    md_text = source.read_text(encoding="utf-8")
    body_html = markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "sane_lists", _codehilite_extension()],
    )
    full_html = (
        f"<html><head><style>{CSS}\n{PYGMENTS_CSS}</style></head>"
        f"<body>{body_html}</body></html>"
    )

    with open(output, "wb") as out:
        result = pisa.CreatePDF(full_html, dest=out)

    if result.err:
        raise RuntimeError(f"PDF generation failed for {source.name} with {result.err} error(s)")

    print(f"Wrote {output}")


def build() -> None:
    for source, output in DOCUMENTS:
        build_one(source, output)


if __name__ == "__main__":
    build()
