from moodle_qc.markdown import code_style, render, same_html, to_markdown

PRE = code_style(1.2)


def test_paragraphs_and_inline_formatting() -> None:
    assert render("Ein `rate()` mit **fett** und *kursiv*.\n\nZweiter Absatz.", pre_style=PRE) == (
        "<p>Ein <code>rate()</code> mit <strong>fett</strong> und <em>kursiv</em>.</p>\n"
        "<p>Zweiter Absatz.</p>"
    )


def test_code_block_gets_the_collection_style_and_escapes_html() -> None:
    markdown = "```\nrate(x[5m]) < 0.1 && y > 2\n\nnext\n```"

    assert render(markdown, pre_style=PRE) == (
        '<pre style="font-family: monospace; line-height: 1.2;">'
        "rate(x[5m]) &lt; 0.1 &amp;&amp; y &gt; 2\n\nnext</pre>"
    )


def test_code_block_language_becomes_a_class() -> None:
    assert render("```yaml\na: 1\n```", pre_style=PRE) == (
        '<pre style="font-family: monospace; line-height: 1.2;" class="language-yaml">a: 1</pre>'
    )


def test_less_than_and_ampersand_in_text_are_escaped_but_raw_html_is_kept() -> None:
    assert render("a < b & c <span>x</span> &amp;", pre_style=PRE) == (
        "<p>a &lt; b &amp; c <span>x</span> &amp;</p>"
    )


def test_raw_html_blocks_pass_through() -> None:
    markdown = "<table><tr><td>1</td></tr></table>\n\n```{=html}\n<div>\n\n</div>\n```"

    assert render(markdown, pre_style=PRE) == "<table><tr><td>1</td></tr></table>\n<div>\n\n</div>"


def test_lists_and_headings() -> None:
    assert render("### Teil A\n\n- eins\n- `zwei`\n\n1. erst\n2. dann", pre_style=PRE) == (
        "<h3>Teil A</h3>\n<ul><li>eins</li><li><code>zwei</code></li></ul>\n"
        "<ol><li>erst</li><li>dann</li></ol>"
    )


def test_gap_markers_stay_untouched() -> None:
    assert render("sum by ([[2]]) ([[3]](x))", pre_style=PRE) == "<p>sum by ([[2]]) ([[3]](x))</p>"


EXPORT_TEXT = (
    "<p>Der Client schreibt <code>0.5</code> und <code>5.0</code>.</p>\n"
    '<pre style="font-family: monospace; line-height: 1.2;">- record: x\n  expr: |\n'
    "    a &gt; [[1]]\n\n- alert: Y</pre>\n"
    "<p>Ziehen Sie die Begriffe in die Lücken.</p>"
)


def test_moodle_html_becomes_markdown() -> None:
    assert to_markdown(EXPORT_TEXT, pre_style=PRE) == (
        "Der Client schreibt `0.5` und `5.0`.\n\n"
        "```\n- record: x\n  expr: |\n    a > [[1]]\n\n- alert: Y\n```\n\n"
        "Ziehen Sie die Begriffe in die Lücken."
    )


def test_markdown_from_html_renders_back_to_the_same_html() -> None:
    assert same_html(render(to_markdown(EXPORT_TEXT, pre_style=PRE), pre_style=PRE), EXPORT_TEXT)


def test_code_block_with_another_style_stays_raw_html() -> None:
    html = '<pre style="font-family: monospace; line-height: 2.2;">a\n\nb</pre>'

    assert to_markdown(html, pre_style=PRE) == f"```{{=html}}\n{html}\n```"


def test_unsupported_inline_html_keeps_the_block_as_raw_html() -> None:
    html = '<p>Text mit <span style="color: red">Farbe</span></p>\n<p>Normal</p>'

    assert to_markdown(html, pre_style=PRE) == (
        '<p>Text mit <span style="color: red">Farbe</span></p>\n\nNormal'
    )


def test_text_that_would_render_differently_stays_raw_html() -> None:
    html = "<p>- kein Listenpunkt</p>"

    assert to_markdown(html, pre_style=PRE) == html


def test_lists_headings_links_and_emphasis() -> None:
    html = (
        '<h3>Teil A</h3><ul><li><strong>eins</strong></li><li><a href="https://x.ch">zwei</a></li>'
        "</ul><ol><li><em>a</em></li></ol>"
    )

    assert to_markdown(html, pre_style=PRE) == (
        "### Teil A\n\n- **eins**\n- [zwei](https://x.ch)\n\n1. *a*"
    )
