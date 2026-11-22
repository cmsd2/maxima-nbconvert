"""Preprocessors for Maxima notebook export."""

from __future__ import annotations

import base64
import json
import math
import re
import warnings

from nbconvert.preprocessors import Preprocessor
from traitlets import Bool, Integer


class PlotlyToSvgPreprocessor(Preprocessor):
    """Convert Plotly JSON outputs to static SVG using Kaleido.

    Looks for outputs with MIME type ``application/x-maxima-plotly`` and adds
    an ``image/svg+xml`` representation using Plotly's static image export.
    If plotly or kaleido is not installed, the preprocessor is silently skipped.
    """

    enabled = Bool(True, help="Enable Plotly to SVG conversion").tag(config=True)
    width = Integer(800, help="SVG output width in pixels").tag(config=True)
    height = Integer(500, help="SVG output height in pixels").tag(config=True)

    # Kaleido export format and the MIME type the result is stored under.
    image_format = "svg"
    target_mime = "image/svg+xml"

    def _encode(self, image_bytes: bytes) -> str:
        return image_bytes.decode("utf-8")

    PLOTLY_MIMES = frozenset(
        {
            "application/x-maxima-plotly",
            "application/vnd.plotly.v1+json",
        }
    )

    def preprocess_cell(self, cell, resources, cell_index):
        """Process each cell, converting Plotly outputs to SVG."""
        if cell.get("cell_type") != "code":
            return cell, resources

        for output in cell.get("outputs", []):
            if output.get("output_type") not in ("display_data", "execute_result"):
                continue

            data = output.get("data", {})
            plotly_mime = next(
                (mime for mime in self.PLOTLY_MIMES if mime in data), None
            )
            if plotly_mime is None:
                continue

            try:
                import plotly.io as pio
            except ImportError:
                warnings.warn(
                    "plotly is not installed; Plotly charts will not be "
                    "converted to SVG. Install with: pip install maxima-nbconvert[plotly]",
                    stacklevel=2,
                )
                return cell, resources

            plotly_json = data[plotly_mime]
            if isinstance(plotly_json, list):
                plotly_json = "".join(plotly_json)
            if isinstance(plotly_json, str):
                fig_dict = json.loads(plotly_json)
            else:
                fig_dict = plotly_json

            try:
                image_bytes = pio.to_image(
                    fig_dict,
                    format=self.image_format,
                    width=self.width,
                    height=self.height,
                )
                data[self.target_mime] = self._encode(image_bytes)
            except Exception as exc:
                warnings.warn(
                    f"Plotly to {self.image_format.upper()} conversion failed "
                    f"for cell {cell_index}: {exc}",
                    stacklevel=2,
                )

        return cell, resources


#: MIME type under which PlotlyToHtmlPreprocessor stores the figure JSON
#: for the ``maxima`` HTML template.  The JSON is compact, rounded, and safe
#: to place inside a ``<script>`` element.
PLOTLY_HTML_MIME = "application/vnd.maxima-nbconvert.plotly+json"

#: plotly.js's own height for figures whose layout sets none.
DEFAULT_PLOTLY_HEIGHT = 450

# Top-level figure keys plotly.js understands.  Others (Aximar's
# ``_reactive`` block, which needs a live kernel) are dropped.
_FIGURE_KEYS = ("data", "layout", "frames")


def _round_floats(obj, digits: int):
    """Round every float in ``obj`` to ``digits`` significant digits.

    Non-finite floats become ``None``: JSON has no NaN or Infinity, and
    plotly.js draws ``null`` as a gap.  ``digits <= 0`` keeps full precision.
    """
    if isinstance(obj, float):
        if not math.isfinite(obj):
            return None
        if digits <= 0:
            return obj
        return float(f"{obj:.{digits}g}")
    if isinstance(obj, list):
        return [_round_floats(x, digits) for x in obj]
    if isinstance(obj, dict):
        return {k: _round_floats(v, digits) for k, v in obj.items()}
    return obj


def _script_safe_json(obj) -> str:
    """Serialise ``obj`` as compact JSON that cannot close a ``<script>``.

    Escaping ``<``, ``>`` and ``&`` as ``\\u`` sequences keeps strings such as
    ``"</script>"`` or ``"<!--"`` in plot titles from ending the element.
    JSON.parse reads the escapes back as the original characters.
    """
    text = json.dumps(obj, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return (
        text.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def _load_figure(value):
    if isinstance(value, list):
        value = "".join(value)
    if isinstance(value, str):
        return json.loads(value)
    return value


class PlotlyToHtmlPreprocessor(Preprocessor):
    """Prepare Plotly outputs for interactive rendering in HTML export.

    For each ``application/x-maxima-plotly`` (or Plotly's own MIME type)
    output, stores the figure's data, layout and frames under
    :data:`PLOTLY_HTML_MIME`.  The ``maxima`` template embeds that JSON and
    draws it with plotly.js when the page loads.

    With ``static_fallback`` enabled it also adds a Kaleido SVG, which the
    page shows until plotly.js has drawn the chart (and keeps showing if
    JavaScript is off or plotly.js fails to load).  That roughly doubles the
    space each plot takes, so it is off by default.
    """

    enabled = Bool(True, help="Enable interactive Plotly output").tag(config=True)
    float_precision = Integer(
        7,
        help=(
            "Round floats in embedded Plotly figures to this many significant "
            "digits, which roughly halves their size. 0 keeps full precision."
        ),
    ).tag(config=True)
    static_fallback = Bool(
        False,
        help=(
            "Also embed a static SVG of each Plotly chart (needs plotly and "
            "kaleido), shown until plotly.js draws the chart."
        ),
    ).tag(config=True)

    def preprocess_cell(self, cell, resources, cell_index):
        if cell.get("cell_type") != "code":
            return cell, resources

        for output in cell.get("outputs", []):
            if output.get("output_type") not in ("display_data", "execute_result"):
                continue

            data = output.get("data", {})
            plotly_mime = next(
                (m for m in PlotlyToSvgPreprocessor.PLOTLY_MIMES if m in data), None
            )
            if plotly_mime is None:
                continue

            try:
                fig = _load_figure(data[plotly_mime])
            except ValueError as exc:
                warnings.warn(
                    f"Could not parse Plotly JSON in cell {cell_index}: {exc}",
                    stacklevel=2,
                )
                continue

            fig = {k: fig[k] for k in _FIGURE_KEYS if fig.get(k)}
            fig = _round_floats(fig, self.float_precision)
            data[PLOTLY_HTML_MIME] = _script_safe_json(fig)
            # The template reserves this height so the page does not jump
            # when charts are drawn as they scroll into view.
            height = fig.get("layout", {}).get("height")
            if not isinstance(height, (int, float)) or height <= 0:
                height = DEFAULT_PLOTLY_HEIGHT
            output.setdefault("metadata", {})[PLOTLY_HTML_MIME] = {"height": int(height)}
            resources["maxima_plotly_count"] = resources.get("maxima_plotly_count", 0) + 1

        if self.static_fallback:
            svg = PlotlyToSvgPreprocessor(parent=self)
            cell, resources = svg.preprocess_cell(cell, resources, cell_index)

        return cell, resources


class PlotlyToPdfPreprocessor(PlotlyToSvgPreprocessor):
    """Convert Plotly JSON outputs to vector PDF for the LaTeX/PDF exporter.

    LaTeX can include PDF figures directly, whereas SVG would need Inkscape
    via nbconvert's SVG2PDFPreprocessor. The PDF is stored base64-encoded
    under ``application/pdf`` so ExtractOutputPreprocessor writes it to disk.
    """

    enabled = Bool(True, help="Enable Plotly to PDF conversion").tag(config=True)

    image_format = "pdf"
    target_mime = "application/pdf"

    def _encode(self, image_bytes: bytes) -> str:
        return base64.b64encode(image_bytes).decode("ascii")


def _preprocess_latex(latex: str) -> str:
    """Clean up Maxima's tex() output for KaTeX compatibility.

    Mirrors the logic in aximar's katex-helpers.ts.
    """
    result = latex

    # Replace {\it content} with \mathit{content}
    result = re.sub(r"\{\\it\s+([^}]*)\}", r"\\mathit{\1}", result)

    # Strip \ifx\endpmatrix\undefined conditionals, keep the LaTeX branch
    result = result.replace(
        r"\ifx\endpmatrix\undefined\pmatrix{\else\begin{pmatrix}\fi",
        r"\begin{pmatrix}",
    )
    result = result.replace(
        r"\ifx\endpmatrix\undefined}\else\end{pmatrix}\fi",
        r"\end{pmatrix}",
    )

    # Replace \cr row separators with \\ (strip trailing \cr before \end)
    result = re.sub(r"\\cr\s*\\end\{pmatrix\}", r"\\end{pmatrix}", result)
    result = result.replace(r"\cr", r"\\")

    # Replace \mbox with \text (better KaTeX support)
    result = result.replace(r"\mbox{", r"\text{")

    # Handle plain \pmatrix{...} (older Maxima versions) with balanced braces
    result = _replace_pmatrix(result)

    return result


def _replace_pmatrix(latex: str) -> str:
    """Convert \\pmatrix{...} to \\begin{pmatrix}...\\end{pmatrix}."""
    prefix = r"\pmatrix{"
    result = []
    i = 0

    while i < len(latex):
        idx = latex.find(prefix, i)
        if idx == -1:
            result.append(latex[i:])
            break

        result.append(latex[i:idx])
        content_start = idx + len(prefix)

        # Walk forward counting braces to find the matching close
        depth = 1
        j = content_start
        while j < len(latex) and depth > 0:
            if latex[j] == "{":
                depth += 1
            elif latex[j] == "}":
                depth -= 1
            j += 1

        if depth == 0:
            content = latex[content_start : j - 1]
            content = re.sub(r"\\cr\s*$", "", content)
            content = content.replace(r"\cr", r"\\")
            result.append(r"\begin{pmatrix}" + content + r"\end{pmatrix}")
            i = j
        else:
            result.append(prefix)
            i = content_start

    return "".join(result)


class MaximaLatexPreprocessor(Preprocessor):
    """Clean up Maxima's tex() output for KaTeX rendering.

    Maxima's tex() emits plain TeX / LaTeX compatibility conditionals
    (e.g. ``\\ifx\\endpmatrix\\undefined``) and uses ``\\cr`` for row
    separators. This preprocessor rewrites them into standard LaTeX
    that KaTeX can render.
    """

    enabled = Bool(True, help="Enable Maxima LaTeX cleanup").tag(config=True)

    def preprocess_cell(self, cell, resources, cell_index):
        if cell.get("cell_type") != "code":
            return cell, resources

        for output in cell.get("outputs", []):
            if output.get("output_type") not in ("display_data", "execute_result"):
                continue

            data = output.get("data", {})
            if "text/latex" in data:
                latex = data["text/latex"]
                if isinstance(latex, list):
                    latex = "".join(latex)
                data["text/latex"] = _preprocess_latex(latex)

        return cell, resources
