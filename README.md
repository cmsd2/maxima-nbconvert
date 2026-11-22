# maxima-nbconvert

nbconvert templates and exporters for [Maxima Notebook](https://marketplace.visualstudio.com/items?itemName=cmsd2.maxima-notebook) (`.macnb`) files.

## Installation

```bash
uv pip install "maxima-nbconvert[plotly]"
```

Or with pip:

```bash
pip install "maxima-nbconvert[plotly]"
```

HTML export draws Plotly charts with plotly.js and needs no extra packages. The `[plotly]` extra installs Plotly and Kaleido, which the PDF and Markdown exporters (and the HTML options below that produce static images or inline plotly.js) use to render charts as images. Without it, those exporters skip Plotly charts.

## Usage

```bash
# Export to HTML
jupyter nbconvert --to maxima_html notebook.macnb

# Export to PDF (requires xelatex)
jupyter nbconvert --to maxima_pdf notebook.macnb
```

## What gets exported

| Notebook Output | Export Result |
|---|---|
| LaTeX math (`text/latex`) | Rendered via MathJax (HTML) or native LaTeX (PDF) |
| gnuplot plots (`image/svg+xml`) | Embedded SVG |
| Plotly charts (`application/x-maxima-plotly`) | Interactive plotly.js chart (HTML), static SVG via Kaleido (Markdown), vector PDF figure (PDF) |
| Text output (`text/plain`) | Preformatted text |
| Errors | Styled error block |

## HTML export notes

Plotly charts stay interactive: hover, zoom, pan and the play button and slider of ax-plots `animate(...)` figures all work on the exported page. Each page with charts loads plotly.js once, from jsDelivr (pinned to the version Aximar bundles), and draws each chart as it scrolls into view. Floats in the embedded figures are rounded to 7 significant digits, which roughly halves their size.

Options (pass as `--Class.option=value`):

| Option | Default | Effect |
|---|---|---|
| `MaximaHTMLExporter.interactive_plotly` | `True` | `False` embeds static SVG images instead, as before |
| `MaximaHTMLExporter.embed_plotly_js` | `False` | Inline plotly.js (about 4.8 MB) so the page works offline; needs the `[plotly]` extra |
| `MaximaHTMLExporter.plotly_js_url` | jsDelivr URL | Where pages load plotly.js from |
| `PlotlyToHtmlPreprocessor.float_precision` | `7` | Significant digits kept in figure data; `0` keeps full precision |
| `PlotlyToHtmlPreprocessor.static_fallback` | `False` | Also embed a Kaleido SVG, shown until plotly.js draws the chart or when JavaScript is off |

## PDF export notes

`maxima_pdf` uses the `maxima_latex` template, which extends nbconvert's stock LaTeX template:

- Maxima LaTeX outputs without math delimiters (as Aximar saves them) go into display math, scaled down to the text width when too wide.
- Plotly charts become vector PDF figures, so no Inkscape is needed.
- Under XeLaTeX, DejaVu fonts are used when installed (by name via fontconfig, or from TeX Live's `dejavu` package), so Unicode in markdown and code renders.
- Notebooks whose headings carry their own numbers can turn off LaTeX's section numbering:

  ```json
  "metadata": { "maxima_nbconvert": { "number_sections": false } }
  ```

On Debian/Ubuntu, `apt install pandoc texlive-xetex texlive-latex-extra texlive-fonts-recommended texlive-plain-generic lmodern fonts-dejavu-core` provides everything the PDF build needs.

## VS Code Integration

The [Maxima Notebook](https://marketplace.visualstudio.com/items?itemName=cmsd2.maxima-notebook) VS Code extension provides "Export Notebook to HTML" and "Export Notebook to PDF" commands that use this package under the hood.

## Development

```bash
git clone https://github.com/cmsd2/maxima-nbconvert.git
cd maxima-nbconvert
uv pip install -e ".[plotly]"
uv run pytest
```

## License

MIT
