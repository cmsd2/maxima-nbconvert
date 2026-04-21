"""Preprocessor that converts application/x-maxima-plotly outputs to SVG."""

from __future__ import annotations

import json
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
