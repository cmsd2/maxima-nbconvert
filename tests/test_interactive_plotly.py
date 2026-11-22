"""Tests for interactive Plotly output in the maxima_html exporter."""

from __future__ import annotations

import json
import math
import re

import nbformat
import pytest
from nbformat.v4 import new_code_cell, new_notebook, new_output

from maxima_nbconvert.exporters import PLOTLY_JS_CDN_URL, MaximaHTMLExporter
from maxima_nbconvert.preprocessors import _round_floats, _script_safe_json

FIGURE_RE = re.compile(
    r'<script class="maxima-plotly-figure" type="application/json">(.*?)</script>',
    re.S,
)


def plotly_cell(fig: dict) -> nbformat.NotebookNode:
    cell = new_code_cell("ax_draw2d(...)$")
    cell.outputs = [
        new_output(
            "display_data",
            data={"application/x-maxima-plotly": json.dumps(fig)},
        )
    ]
    return cell


def notebook(*figs: dict) -> nbformat.NotebookNode:
    return new_notebook(cells=[plotly_cell(f) for f in figs])


def figures_in(html: str) -> list[dict]:
    return [json.loads(m) for m in FIGURE_RE.findall(html)]


LINE = {
    "data": [{"type": "scatter", "x": [0.0, 0.1234567891234, 1.0], "y": [1, 2, 3]}],
    "layout": {"title": {"text": "line"}, "width": 700, "height": 600},
}

ANIMATED = {
    "data": [{"type": "scatter", "x": [0, 1], "y": [0, 0]}],
    "layout": {"sliders": [{"steps": []}], "updatemenus": [{"buttons": []}]},
    "frames": [
        {"name": "0", "data": [{"y": [0, 1]}]},
        {"name": "1", "data": [{"y": [1, 0]}]},
    ],
    "_reactive": {"view_id": 3, "signals": []},
}


def test_round_floats_keeps_significant_digits():
    assert _round_floats(0.1234567891234, 7) == 0.1234568
    assert _round_floats(123456789.0, 3) == 123000000.0
    assert _round_floats(1e-12 + 1e-20, 7) == 1e-12


def test_round_floats_leaves_ints_and_strings():
    obj = {"x": [1, 2, 3], "name": "θ1", "flag": True}
    assert _round_floats(obj, 3) == obj


def test_round_floats_replaces_non_finite_with_null():
    assert _round_floats([math.nan, math.inf, -math.inf, 1.0], 7) == [None, None, None, 1.0]


def test_round_floats_zero_digits_keeps_precision():
    assert _round_floats(0.1234567891234, 0) == 0.1234567891234


def test_script_safe_json_cannot_close_script():
    obj = {"title": "</script><script>alert(1)</script> & <!--  "}
    text = _script_safe_json(obj)
    assert "<" not in text and ">" not in text and "&" not in text
    assert " " not in text
    assert json.loads(text) == obj


def test_html_embeds_figures_and_loads_plotly_once():
    html, resources = MaximaHTMLExporter().from_notebook_node(notebook(LINE, ANIMATED))

    assert resources["maxima_plotly_count"] == 2
    assert html.count(PLOTLY_JS_CDN_URL) == 1
    assert 'data-mime-type="image/svg+xml"' not in html

    line, animated = figures_in(html)
    assert line["data"][0]["x"] == [0.0, 0.1234568, 1.0]
    assert line["layout"]["width"] == 700
    assert animated["frames"] == ANIMATED["frames"]
    assert "_reactive" not in animated
    assert "addFrames" in html


def test_html_reserves_chart_height():
    html, _ = MaximaHTMLExporter().from_notebook_node(notebook(LINE, ANIMATED))
    heights = re.findall(r'class="maxima-plotly" style="min-height: (\d+)px"', html)
    assert heights == ["600", "450"]


def test_html_without_plots_does_not_load_plotly():
    nb = new_notebook(cells=[new_code_cell("1+1;")])
    html, _ = MaximaHTMLExporter().from_notebook_node(nb)
    assert "plotly.min.js" not in html
    assert "Plotly.newPlot" not in html


def test_html_title_cannot_break_out_of_script():
    fig = {"data": [], "layout": {"title": {"text": "</script><b>x</b>"}}}
    html, _ = MaximaHTMLExporter().from_notebook_node(notebook(fig))
    assert "<b>x</b>" not in html
    assert figures_in(html)[0]["layout"]["title"]["text"] == "</script><b>x</b>"


def test_float_precision_is_configurable():
    from traitlets.config import Config

    config = Config({"PlotlyToHtmlPreprocessor": {"float_precision": 3}})
    html, _ = MaximaHTMLExporter(config=config).from_notebook_node(notebook(LINE))
    assert figures_in(html)[0]["data"][0]["x"] == [0.0, 0.123, 1.0]


def test_embed_plotly_js_inlines_library():
    pytest.importorskip("plotly")
    exporter = MaximaHTMLExporter(embed_plotly_js=True)
    html, _ = exporter.from_notebook_node(notebook(LINE))
    assert PLOTLY_JS_CDN_URL not in html
    assert len(html) > 3_000_000


def test_static_fallback_adds_svg_image():
    pytest.importorskip("kaleido")
    from traitlets.config import Config

    config = Config({"PlotlyToHtmlPreprocessor": {"static_fallback": True}})
    html, _ = MaximaHTMLExporter(config=config).from_notebook_node(notebook(LINE))
    assert '<img alt="" class="maxima-plotly-fallback" src="data:image/svg+xml;base64,' in html
    assert len(figures_in(html)) == 1


def test_interactive_plotly_off_gives_static_svg():
    pytest.importorskip("kaleido")
    exporter = MaximaHTMLExporter(interactive_plotly=False)
    html, _ = exporter.from_notebook_node(notebook(LINE))
    assert 'data-mime-type="image/svg+xml"' in html
    assert "maxima-plotly-figure" not in html
    assert PLOTLY_JS_CDN_URL not in html
