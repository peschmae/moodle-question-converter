import xml.etree.ElementTree as ET
from typing import Any

from moodle_qc.qtypes.ddwtos import DragAndDropIntoText, Dragbox, layout
from moodle_qc.question import RenderedText
from moodle_qc.source import SourceDocument
from moodle_qc.xmlnode import Node, serialize
from tests.support.questions import question

HANDLER = DragAndDropIntoText()


def gap_question(text: str, **settings: Any) -> Any:
    return question("ddwtos", text=text, **settings)


def test_gaps_are_numbered_and_groups_follow_the_distractors_order() -> None:
    gaps = layout(
        "```\n[[rate|function]] by ([[service|label]]) [[irate_x]]\n```",
        {"distractors": {"label": ["pod"], "function": ["irate"]}},
    )

    assert gaps.text == "```\n[[1]] by ([[2]]) [[3]]\n```"
    assert gaps.groups == ["label", "function", ""]
    assert gaps.dragboxes == [
        Dragbox("rate", "function"),
        Dragbox("service", "label"),
        Dragbox("irate_x", ""),
        Dragbox("pod", "label"),
        Dragbox("irate", "function"),
    ]


def test_same_word_in_two_gap_groups_gets_two_dragboxes() -> None:
    gaps = layout("[[count|suffix]] [[count|function]]", {})

    assert [(box.word, box.group) for box in gaps.dragboxes] == [
        ("count", "suffix"),
        ("count", "function"),
    ]


def test_reusable_group_shares_one_dragbox_and_writes_infinite() -> None:
    q = gap_question(
        "[[a|kw]] und [[a|kw]] [[b|op]]", distractors={"kw": ["c"], "op": ["d"]}, reusable=["kw"]
    )
    node = Node("question")

    HANDLER.write(q, node, lambda md: RenderedText(md))

    assert HANDLER.question_text(q) == "[[1]] und [[1]] [[2]]"
    element = ET.fromstring(serialize(node))
    assert [
        (b.findtext("text"), b.find("infinite") is not None) for b in element.findall("dragbox")
    ] == [
        ("a", True),
        ("b", False),
        ("c", True),
        ("d", False),
    ]


def test_validation_rules() -> None:
    assert HANDLER.validate(gap_question("Kein Gap")) == [
        "has no gaps; write them as [[word|group]] in the question text"
    ]
    assert HANDLER.validate(
        gap_question("[[a|x]] [[b|y]]", distractors={"x": ["c"], "z": ["d"]})
    ) == [
        "gap group 'z' has distractors but no gap uses it",
        "gap group 'y' has no distractor",
    ]
    assert HANDLER.validate(gap_question("[[a]] [[b]]", distractors=["a", "c"])) == [
        "the gaps has the word(s) a more than once"
    ]


def test_reading_puts_words_back_and_uses_the_existing_group_names() -> None:
    existing = SourceDocument(
        text="[[x|keyword]] [[y|operator]]",
        front_matter={"distractors": {"keyword": ["k"], "operator": ["o"]}},
    )
    element = ET.fromstring(
        "<question><shuffleanswers>1</shuffleanswers>"
        "<dragbox><text>rate</text><group>1</group></dragbox>"
        "<dragbox><text>and</text><group>2</group></dragbox>"
        "<dragbox><text>expr</text><group>1</group></dragbox>"
        "<dragbox><text>or</text><group>2</group></dragbox></question>"
    )

    result = HANDLER.read(element, "[[1]] ... [[2]]", lambda html, files: html, existing)

    assert result.text == "[[rate|keyword]] ... [[and|operator]]"
    assert result.settings["distractors"] == {"keyword": ["expr"], "operator": ["or"]}
