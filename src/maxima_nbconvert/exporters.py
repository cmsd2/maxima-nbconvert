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
    """PDF exporter with Plotly to SVG preprocessing for vector graphics."""

    export_from_notebook = "Maxima PDF"

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
        # Inject our preprocessors *before* the built-in
        # ExtractOutputPreprocessor.  PlotlyToSvg adds an image/svg+xml
        # representation alongside application/x-maxima-plotly;
        # ExtractOutput then writes it to <name>_files/*.svg on disk
        # and rewrites the markdown to link to the file.  If our
        # preprocessors ran *after* ExtractOutput, the new SVGs would
        # get inlined as malformed `data:` URIs that GitHub doesn't
        # render.
        from maxima_nbconvert.preprocessors import (
            MaximaLatexPreprocessor,
            PlotlyToSvgPreprocessor,
        )
        from nbconvert.preprocessors import ExtractOutputPreprocessor

        ours = [MaximaLatexPreprocessor(parent=self),
                PlotlyToSvgPreprocessor(parent=self)]
        for p in ours:
            p.enabled = True

        # Find the ExtractOutput slot (if present) and splice in front of it.
        extract_idx = None
        for i, p in enumerate(self._preprocessors):
            if isinstance(p, ExtractOutputPreprocessor):
                extract_idx = i
                break
        if extract_idx is not None:
            self._preprocessors[extract_idx:extract_idx] = ours
        else:
            self._preprocessors.extend(ours)

    def from_notebook_node(
        self, nb: nbformat.NotebookNode, resources: Optional[dict[str, Any]] = None, **kw: Any
    ) -> tuple[str, dict[str, Any]]:
        _ensure_maxima_language_info(nb)
        return super().from_notebook_node(nb, resources, **kw)
