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

    @property
    def extra_template_basedirs(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return [os.path.join(here, "templates")] + super().extra_template_basedirs

    @default("preprocessors")
    def _preprocessors_default(self):
        preps = list(super()._preprocessors_default())
        preps.append("maxima_nbconvert.preprocessors.PlotlyToSvgPreprocessor")
        return preps


class MaximaPDFExporter(PDFExporter):
    """PDF exporter with Plotly to SVG preprocessing for vector graphics."""

    export_from_notebook = "Maxima PDF"

    @default("preprocessors")
    def _preprocessors_default(self):
        preps = list(super()._preprocessors_default())
        preps.append("maxima_nbconvert.preprocessors.PlotlyToSvgPreprocessor")
        return preps
