"""Custom nbconvert exporters for Maxima notebooks."""

from __future__ import annotations

import os

from nbconvert.exporters import HTMLExporter, PDFExporter
from traitlets import default


class MaximaHTMLExporter(HTMLExporter):
    """HTML exporter with Maxima-specific template and Plotly preprocessing."""

    export_from_notebook = "Maxima HTML"

    @default("template_name")
    def _template_name_default(self):
        return "maxima"

    @default("extra_template_basedirs")
    def _extra_template_basedirs_default(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return [os.path.join(here, "templates"), os.getcwd()]

    def _init_preprocessors(self):
        super()._init_preprocessors()
        self.register_preprocessor(
            "maxima_nbconvert.preprocessors.PlotlyToSvgPreprocessor",
            enabled=True,
        )


class MaximaPDFExporter(PDFExporter):
    """PDF exporter with Plotly to SVG preprocessing for vector graphics."""

    export_from_notebook = "Maxima PDF"

    def _init_preprocessors(self):
        super()._init_preprocessors()
        self.register_preprocessor(
            "maxima_nbconvert.preprocessors.PlotlyToSvgPreprocessor",
            enabled=True,
        )
