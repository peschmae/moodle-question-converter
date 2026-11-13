from moodle_qc.markdown import code_style, render

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
