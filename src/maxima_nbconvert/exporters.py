"""Custom nbconvert exporters for Maxima notebooks."""

from __future__ import annotations

import os
from typing import Any, Optional

import nbformat
from nbconvert.exporters import HTMLExporter, MarkdownExporter, PDFExporter
from traitlets import Bool, Unicode, default
from traitlets.config import Config

from maxima_nbconvert.preprocessors import PLOTLY_HTML_MIME

#: plotly.js release loaded by exported pages.  Matches the version Aximar
#: bundles, so charts look the same in the app and on the page.
PLOTLY_JS_VERSION = "3.5.0"
PLOTLY_JS_CDN_URL = (
    f"https://cdn.jsdelivr.net/npm/plotly.js-dist-min@{PLOTLY_JS_VERSION}/plotly.min.js"
)


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
    """HTML exporter with Maxima-specific template and Plotly preprocessing.

    Plotly charts become live plotly.js charts (hover, zoom, animation
    playback).  Set ``interactive_plotly`` to False for static SVG images.
    """

    export_from_notebook = "Maxima HTML"

    interactive_plotly = Bool(
        True,
        help="Render Plotly charts with plotly.js instead of static SVG images.",
    ).tag(config=True)
    plotly_js_url = Unicode(
        PLOTLY_JS_CDN_URL,
        help="URL pages load plotly.js from when they contain Plotly charts.",
    ).tag(config=True)
    embed_plotly_js = Bool(
        False,
        help=(
            "Inline plotly.js (about 4.8 MB, from the installed plotly package) "
            "into each page that has Plotly charts, so the page works offline."
        ),
    ).tag(config=True)

    @property
    def default_config(self):
        c = super().default_config
        # Our preprocessor's MIME type comes first, so a chart it prepared
        # wins over any static image stored alongside it.
        priority = c.NbConvertBase.display_data_priority
        c.merge(
            Config(
                {
                    "NbConvertBase": {
                        "display_data_priority": [PLOTLY_HTML_MIME, *priority],
                    }
                }
            )
        )
        return c

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
        plotly_preprocessor = (
            "PlotlyToHtmlPreprocessor" if self.interactive_plotly else "PlotlyToSvgPreprocessor"
        )
        self.register_preprocessor(
            f"maxima_nbconvert.preprocessors.{plotly_preprocessor}",
            enabled=True,
        )

    def _plotly_js_resources(self) -> dict[str, Any]:
        if not self.embed_plotly_js:
            return {"url": self.plotly_js_url}
        try:
            from plotly.offline import get_plotlyjs
        except ImportError as exc:
            raise RuntimeError(
                "embed_plotly_js needs the plotly package. Install with: "
                "pip install maxima-nbconvert[plotly]"
            ) from exc
        return {"inline": get_plotlyjs()}

    def from_notebook_node(
        self, nb: nbformat.NotebookNode, resources: Optional[dict[str, Any]] = None, **kw: Any
    ) -> tuple[str, dict[str, Any]]:
        _ensure_maxima_language_info(nb)
        if resources is None:
            resources = {}
        resources["maxima_plotly_js"] = self._plotly_js_resources()
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
