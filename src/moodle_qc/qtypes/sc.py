"""``sc``: Single Choice (ETH plugin). One correct answer, given as ``<correctrow>``."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from moodle_qc.qtypes.base import (
    BaseQuestionType,
    ReadResult,
    flag,
    read_flag,
    read_rows,
    text_of,
    write_rows,
)
from moodle_qc.question import Question, Render, ToMarkdown
from moodle_qc.source import SourceDocument
from moodle_qc.xmlnode import Node

SCORING_METHODS = ("sconezero", "aprime", "subpoints")


class SingleChoice(BaseQuestionType):
    name = "sc"
    front_matter_keys = frozenset({"scoring", "numbering"})
    has_answers = True
    combined_feedback = False

    def validate(self, question: Question) -> list[str]:
        problems: list[str] = []
        correct = sum(answer.correct for answer in question.answers)
        if correct != 1:
            problems.append(f"needs exactly one correct answer ([x]), has {correct}")
        if question.settings.get("scoring") not in SCORING_METHODS:
            problems.append(f"scoring must be one of {', '.join(SCORING_METHODS)}")
        return problems

    def write(self, question: Question, node: Node, render: Render) -> None:
        settings = question.settings
        node.add_text("scoringmethod", str(settings["scoring"]))
        node.add("shuffleanswers", flag(settings["shuffle"]))
        node.add_text("answernumbering", str(settings["numbering"]))
        node.add("numberofrows", str(len(question.answers)))
        correct_row = next((i for i, a in enumerate(question.answers, 1) if a.correct), 1)
        node.add("correctrow", str(correct_row))
        write_rows(node, question.answers, render)

    def read(
        self,
        element: ET.Element,
        text: str,
        to_markdown: ToMarkdown,
        existing: SourceDocument | None = None,
    ) -> ReadResult:
        correct_row = text_of(element, "correctrow")
        answers = []
        for number, answer in read_rows(element, to_markdown):
            answer.correct = number == correct_row
            answers.append(answer)
        return ReadResult(
            settings={
                "scoring": text_of(element, "scoringmethod"),
                "numbering": text_of(element, "answernumbering"),
                "shuffle": read_flag(element.findtext("shuffleanswers")),
            },
            answers=answers,
        )
