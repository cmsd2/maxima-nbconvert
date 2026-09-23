"""Custom nbconvert exporters for Maxima notebooks."""

from __future__ import annotations

import os
from typing import Any, Optional

import nbformat
from nbconvert.exporters import HTMLExporter, MarkdownExporter, PDFExporter
from traitlets import default


def _ensure_maxima_language_info(nb):
    """Ensure notebook metadata includes language_info for Maxima.

    nbconvert picks the Pygments lexer from metadata.language_info.name
    (or .pygments_lexer). Maxima notebooks typically have an empty
    language_info dict, causing nbconvert to fall back to ipython3.
    """
    langinfo = nb.metadata.get("language_info", {})
    if not langinfo.get("pygments_lexer") and not langinfo.get("name"):
        kernel_lang = nb.metadata.get("kernelspec", {}).get("language", "")
        if kernel_lang.lower() == "maxima" or not kernel_lang:
            nb.metadata["language_info"] = {
                **langinfo,
                "name": "maxima",
                "pygments_lexer": "maxima",
            }


def _insert_before_extract_output(exporter, preprocessors):
    """Enable ``preprocessors`` and splice them in front of nbconvert's
    ExtractOutputPreprocessor (or append them if it is not registered).

    Anything that adds an image representation has to run before
    ExtractOutput, which is what writes images to disk and records their
    file names; otherwise templates that reference those file names
    (LaTeX's draw_figure, Markdown image links) find nothing.
    """
    from nbconvert.preprocessors import ExtractOutputPreprocessor

    for p in preprocessors:
        p.enabled = True

    extract_idx = next(
        (i for i, p in enumerate(exporter._preprocessors)
         if isinstance(p, ExtractOutputPreprocessor)),
        None,
    )
    if extract_idx is not None:
        exporter._preprocessors[extract_idx:extract_idx] = preprocessors
    else:
        exporter._preprocessors.extend(preprocessors)


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
            "maxima_nbconvert.preprocessors.MaximaLatexPreprocessor",
            enabled=True,
        )
        self.register_preprocessor(
            "maxima_nbconvert.preprocessors.PlotlyToSvgPreprocessor",
            enabled=True,
        )

    def from_notebook_node(
        self, nb: nbformat.NotebookNode, resources: Optional[dict[str, Any]] = None, **kw: Any
    ) -> tuple[str, dict[str, Any]]:
        _ensure_maxima_language_info(nb)
        return super().from_notebook_node(nb, resources, **kw)


class MaximaPDFExporter(PDFExporter):
    """PDF exporter using the ``maxima_latex`` template, with Plotly charts
    converted to vector PDF figures."""

    export_from_notebook = "Maxima PDF"

    @default("template_name")
    def _template_name_default(self):
        return "maxima_latex"

    @default("extra_template_basedirs")
    def _extra_template_basedirs_default(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return [os.path.join(here, "templates"), os.getcwd()]

    def _init_preprocessors(self):
        super()._init_preprocessors()
        from maxima_nbconvert.preprocessors import (
            MaximaLatexPreprocessor,
            PlotlyToPdfPreprocessor,
        )

        _insert_before_extract_output(
            self,
            [MaximaLatexPreprocessor(parent=self), PlotlyToPdfPreprocessor(parent=self)],
        )

    def from_notebook_node(
        self, nb: nbformat.NotebookNode, resources: Optional[dict[str, Any]] = None, **kw: Any
    ) -> tuple[str, dict[str, Any]]:
        _ensure_maxima_language_info(nb)
        return super().from_notebook_node(nb, resources, **kw)


class MaximaMarkdownExporter(MarkdownExporter):
    """Markdown exporter that cleans up Maxima's tex() output and converts
    Plotly outputs to static SVG. Suitable for in-repo browsing on GitHub
    (which renders ``$$...$$`` blocks via MathJax and links to ``.svg`` files
    in ``_files/`` subdirectories).
    """

    export_from_notebook = "Maxima Markdown"

    @default("template_name")
    def _template_name_default(self):
        return "maxima_markdown"

    @default("extra_template_basedirs")
    def _extra_template_basedirs_default(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return [os.path.join(here, "templates"), os.getcwd()]

    def _init_preprocessors(self):
        super()._init_preprocessors()
        # PlotlyToSvg adds an image/svg+xml representation alongside
        # application/x-maxima-plotly; ExtractOutput then writes it to
        # <name>_files/*.svg on disk and rewrites the markdown to link to
        # the file.  If our preprocessors ran *after* ExtractOutput, the
        # new SVGs would get inlined as malformed `data:` URIs that GitHub
        # doesn't render.
        from maxima_nbconvert.preprocessors import (
            MaximaLatexPreprocessor,
            PlotlyToSvgPreprocessor,
        )

        _insert_before_extract_output(
            self,
            [MaximaLatexPreprocessor(parent=self), PlotlyToSvgPreprocessor(parent=self)],
        )

    def from_notebook_node(
        self, nb: nbformat.NotebookNode, resources: Optional[dict[str, Any]] = None, **kw: Any
    ) -> tuple[str, dict[str, Any]]:
        _ensure_maxima_language_info(nb)
        return super().from_notebook_node(nb, resources, **kw)
