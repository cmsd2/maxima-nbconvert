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

The `[plotly]` extra installs Plotly and Kaleido for converting interactive charts to static SVG images. Without it, Plotly chart outputs will be skipped during export.

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
| Plotly charts (`application/x-maxima-plotly`) | Static SVG via Kaleido (vector PDF figure in PDF export) |
| Text output (`text/plain`) | Preformatted text |
| Errors | Styled error block |

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
```

## License

MIT
