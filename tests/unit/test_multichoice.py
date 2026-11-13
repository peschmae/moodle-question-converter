import xml.etree.ElementTree as ET
from typing import Any

from moodle_qc.qtypes.multichoice import MultiChoice
from moodle_qc.question import RenderedText
from moodle_qc.source import Answer
from moodle_qc.xmlnode import Node, serialize
from tests.support.questions import answers, question

HANDLER = MultiChoice()


def written(*items: Answer, **settings: Any) -> ET.Element:
    node = Node("question", {"type": "multichoice"})
    HANDLER.write(question("multichoice", *items, **settings), node, lambda md: RenderedText(md))
    return ET.fromstring(serialize(node))


def fractions(element: ET.Element) -> list[str]:
    return [answer.get("fraction", "") for answer in element.findall("answer")]


def test_one_correct_answer_means_radio_buttons() -> None:
    element = written(*answers(False, True, False))

    assert element.findtext("single") == "true"
    assert fractions(element) == ["0", "100", "0"]


def test_several_correct_answers_share_100_percent_and_wrong_ones_deduct_the_same() -> None:
    element = written(*answers(True, True, True, False))

    assert element.findtext("single") == "false"
    assert fractions(element) == ["33.33333", "33.33333", "33.33333", "-33.33333"]


def test_multiple_true_with_one_correct_answer_uses_checkboxes() -> None:
    element = written(*answers(True, False, False), multiple=True)

    assert element.findtext("single") == "false"
    assert fractions(element) == ["100", "-100", "-100"]


def test_percentage_override_for_one_answer() -> None:
    items = [
        Answer("a", True, fraction=50),
        Answer("b", True, fraction=50),
        Answer("c", False, fraction=-25),
    ]

    assert fractions(written(*items)) == ["50", "50", "-25"]


def test_answer_feedback_is_written() -> None:
    element = written(Answer("a", True, "Gut"), Answer("b", False))

    assert [a.findtext("feedback/text") for a in element.findall("answer")] == ["Gut", ""]


def test_needs_a_correct_answer() -> None:
    assert HANDLER.validate(question("multichoice", *answers(False, False))) == [
        "needs at least one correct answer ([x])"
    ]


def test_percentages_moodle_does_not_accept_are_reported() -> None:
    eleven = answers(*([True] * 11))

    assert HANDLER.validate(question("multichoice", *eleven))[0].startswith(
        "answer 1 gets 9.09091%, which Moodle doesn't accept"
    )


def test_correct_percentages_must_add_up_to_100() -> None:
    items = [Answer("a", True, fraction=50), Answer("b", True, fraction=40)]

    assert HANDLER.validate(question("multichoice", *items)) == [
        "the correct answers add up to 90%, not 100%"
    ]


def test_reading_restores_overrides_only_where_they_differ() -> None:
    element = written(Answer("a", True, fraction=50), Answer("b", True), Answer("c", False))

    result = HANDLER.read(element, "", lambda html, files: html)

    assert [(a.correct, a.fraction) for a in result.answers or []] == [
        (True, None),
        (True, None),
        (False, None),
    ]
