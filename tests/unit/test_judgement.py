import xml.etree.ElementTree as ET

from moodle_qc.qtypes.judgement import KPrime, MultipleTrueFalse
from moodle_qc.question import RenderedText
from moodle_qc.xmlnode import Node, serialize
from tests.support.questions import answers, question


def test_kprime_needs_exactly_four_answers() -> None:
    assert KPrime().validate(question("kprime", *answers(True, False, True))) == [
        "needs exactly four answers, has 3"
    ]


def test_scoring_method_must_fit_the_question_type() -> None:
    assert MultipleTrueFalse().validate(question("mtf", *answers(True), scoring="kprime")) == [
        "scoring must be one of subpoints, mtfonezero, subpointdeduction"
    ]


def test_correct_judgement_is_the_column_with_weight_above_zero() -> None:
    node = Node("question")
    KPrime().write(
        question("kprime", *answers(True, False, True, False), labels=["richtig", "falsch"]),
        node,
        lambda md: RenderedText(md),
    )
    element = ET.fromstring(serialize(node))

    weights = {
        (w.get("rownumber"), w.get("columnnumber")): w.findtext("value")
        for w in element.findall("weight")
    }
    assert weights[("1", "1")] == "1.000" and weights[("1", "2")] == "0.000"
    assert weights[("2", "1")] == "0.000" and weights[("2", "2")] == "1.000"
    assert [c.findtext("responsetext/text") for c in element.findall("column")] == [
        "richtig",
        "falsch",
    ]
    assert element.find("deduction") is None


def test_mtf_writes_numbering_and_deduction_and_reads_them_back() -> None:
    node = Node("question")
    handler = MultipleTrueFalse()
    handler.write(
        question("mtf", *answers(True, False), deduction=0.5), node, lambda md: RenderedText(md)
    )
    element = ET.fromstring(serialize(node))

    assert element.findtext("answernumbering") == "none"
    assert element.findtext("deduction") == "0.5"
    result = handler.read(element, "", lambda html, files: html)
    assert result.settings["deduction"] == 0.5
    assert [a.correct for a in result.answers or []] == [True, False]
