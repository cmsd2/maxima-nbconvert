"""Preprocessors for Maxima notebook export."""

from __future__ import annotations

import json
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
                svg_bytes = pio.to_image(
                    fig_dict,
                    format="svg",
                    width=self.width,
                    height=self.height,
                )
                svg_str = svg_bytes.decode("utf-8")
                data["image/svg+xml"] = svg_str
            except Exception as exc:
                warnings.warn(
                    f"Plotly to SVG conversion failed for cell {cell_index}: {exc}",
                    stacklevel=2,
                )

        return cell, resources


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
