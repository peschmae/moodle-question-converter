from pathlib import Path

import pytest

from tests.support.moodle_xml_compare import assert_moodle_xml_equal, compare_moodle_xml

FIXTURES = Path(__file__).parent.parent / "fixtures" / "moodle"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_reference_file_and_moodle_reexport_compare_equal() -> None:
    differences = compare_moodle_xml(
        fixture("moodle-xml-reference.xml"),
        fixture("moodle-xml-reference.reexport.xml"),
    )

    assert differences == []


def test_changed_answer_fraction_is_reported_with_location_and_values() -> None:
    reexport = fixture("moodle-xml-reference.reexport.xml")
    changed = reexport.replace(
        '<answer fraction="50" format="html">', '<answer fraction="25" format="html">', 1
    )

    differences = compare_moodle_xml(fixture("moodle-xml-reference.xml"), changed)

    assert [str(d) for d in differences] == [
        "question import-test/SW07/SW07 – Prometheus Datenmodell (multichoice) > answer[1] @fraction: "
        "expected '50', got '25'"
    ]


def quiz(*questions: str) -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n<quiz>' + "".join(questions) + "</quiz>"


SC_COMPACT = """<question type="sc"><name><text>Error Budget</text></name>
<questiontext format="html"><text><![CDATA[<p>Was ist <b>1 - SLO</b> & warum?</p>
<pre>a  <  b</pre>]]></text></questiontext><defaultgrade>1</defaultgrade><idnumber></idnumber>
<correctrow>2</correctrow></question>"""

SC_ESCAPED = """
  <!-- question: 8997103  -->
  <question type="sc">
    <name>
      <text>Error Budget</text>
    </name>
    <questiontext format="html">
      <text>&lt;p&gt;Was ist &lt;b&gt;1 - SLO&lt;/b&gt; &amp; warum?&lt;/p&gt;&lt;pre&gt;a  &lt;  b&lt;/pre&gt;</text>
    </questiontext>
    <defaultgrade>1.0000000</defaultgrade>
    <correctrow>2</correctrow>
  </question>
"""


def test_formatting_differences_are_ignored() -> None:
    assert compare_moodle_xml(quiz(SC_COMPACT), quiz(SC_ESCAPED)) == []


def test_whitespace_inside_text_is_compared() -> None:
    changed = SC_COMPACT.replace("a  <  b", "a < b")

    differences = compare_moodle_xml(quiz(SC_COMPACT), quiz(changed))

    assert [d.location for d in differences] == ["question Error Budget (sc) > questiontext > text"]


def test_missing_and_extra_questions_are_reported() -> None:
    other = SC_COMPACT.replace("Error Budget", "SLO")

    differences = compare_moodle_xml(quiz(SC_COMPACT), quiz(other))

    assert [str(d) for d in differences] == [
        "question Error Budget (sc): expected 'present', got None",
        "question SLO (sc): expected None, got 'present'",
    ]


def test_questions_are_matched_by_category_and_question_id() -> None:
    def in_category(path: str, question_id: str) -> str:
        category = f'<question type="category"><category><text>{path}</text></category></question>'
        return category + SC_COMPACT.replace(
            "<idnumber></idnumber>", f"<idnumber>{question_id}</idnumber>"
        )

    expected = quiz(in_category("sw09", "a"), in_category("sw10", "b"))
    actual = quiz(
        '<question type="category"><category><text>$course$/top</text></category></question>',
        in_category("$course$/top/sw10", "b"),
        in_category("$course$/top/sw09", "a"),
    )

    assert compare_moodle_xml(expected, actual) == []


def test_assert_lists_every_difference() -> None:
    changed = SC_COMPACT.replace("<correctrow>2</correctrow>", "<correctrow>1</correctrow>")

    with pytest.raises(AssertionError) as failure:
        assert_moodle_xml_equal(quiz(SC_COMPACT), quiz(changed))

    assert str(failure.value) == (
        "Moodle XML differs in 1 place(s):\n"
        "  - question Error Budget (sc) > correctrow: expected '2', got '1'"
    )


def category(path: str, info: str = "") -> str:
    return (
        f'<question type="category"><category><text>{path}</text></category>'
        f'<info format="html"><text>{info}</text></info></question>'
    )


def test_missing_category_and_changed_category_info_are_reported() -> None:
    expected = quiz(category("sw09", "Alerting"), SC_COMPACT, category("sw10"))
    actual = quiz(category("$course$/top/sw09", "Dashboards"), SC_COMPACT)

    assert [str(d) for d in compare_moodle_xml(expected, actual)] == [
        "category sw09 > info: expected 'Alerting', got 'Dashboards'",
        "category sw10: expected 'present', got None",
    ]


def test_line_breaks_and_indentation_inside_code_blocks_are_compared() -> None:
    def with_code(code: str) -> str:
        return SC_COMPACT.replace("<pre>a  <  b</pre>", f"<pre><code>{code}</code></pre>")

    one_line = with_code("<span>def f():</span><span>return 1</span>")
    two_lines = with_code("<span>def f():</span>\n    <span>return 1</span>")

    differences = compare_moodle_xml(quiz(one_line), quiz(two_lines))

    assert [d.location for d in differences] == ["question Error Budget (sc) > questiontext > text"]


def test_only_plain_decimal_numbers_are_compared_numerically() -> None:
    def with_answer(text: str) -> str:
        return SC_COMPACT.replace("<correctrow>2</correctrow>", f"<correctrow>{text}</correctrow>")

    assert compare_moodle_xml(quiz(with_answer("1")), quiz(with_answer("1.0000000"))) == []
    assert compare_moodle_xml(quiz(with_answer("0.5")), quiz(with_answer(".5"))) != []
    assert compare_moodle_xml(quiz(with_answer("10")), quiz(with_answer("1_0"))) != []


def test_questions_with_the_same_name_are_all_compared() -> None:
    first = SC_COMPACT.replace("<correctrow>2</correctrow>", "<correctrow>1</correctrow>")

    differences = compare_moodle_xml(quiz(first, SC_COMPACT), quiz(SC_COMPACT))

    assert [str(d) for d in differences] == [
        "question Error Budget (sc) > correctrow: expected '1', got '2'",
        "question Error Budget (sc): expected 'present', got None",
    ]


def test_long_text_differences_point_to_the_first_changed_place() -> None:
    long_text = "Beurteilen Sie die folgenden Aussagen zum OpenTelemetry Collector sorgfältig."
    expected = SC_COMPACT.replace("Was ist", long_text)
    actual = expected.replace("Collector", "Kollektor")

    [difference] = compare_moodle_xml(quiz(expected), quiz(actual))

    assert str(difference) == (
        "question Error Budget (sc) > questiontext > text: at character 59: "
        "expected '…n zum OpenTelemetry Collector sorgfältig…', "
        "got '…n zum OpenTelemetry Kollektor sorgfältig…'"
    )
