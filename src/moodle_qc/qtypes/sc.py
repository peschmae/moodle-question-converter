"""``sc``: Single Choice (ETH plugin). One correct answer, given as ``<correctrow>``."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from moodle_qc.qtypes.base import ReadResult, add_field, flag, read_field, read_flag, text_of
from moodle_qc.question import Question, Render, ToMarkdown
from moodle_qc.source import Answer
from moodle_qc.xmlnode import Node

SCORING_METHODS = ("sconezero", "aprime", "subpoints")


class SingleChoice:
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
        for number, answer in enumerate(question.answers, 1):
            row = node.add("row", number=str(number))
            add_field(row, "optiontext", answer.text, render)
            add_field(row, "feedbacktext", answer.feedback, render)

    def read(self, element: ET.Element, text: str, to_markdown: ToMarkdown) -> ReadResult:
        correct_row = text_of(element, "correctrow")
        answers = [
            Answer(
                read_field(row.find("optiontext"), to_markdown),
                row.get("number") == correct_row,
                read_field(row.find("feedbacktext"), to_markdown),
            )
            for row in sorted(element.findall("row"), key=lambda r: int(r.get("number", "0")))
        ]
        return ReadResult(
            settings={
                "scoring": text_of(element, "scoringmethod"),
                "numbering": text_of(element, "answernumbering"),
                "shuffle": read_flag(element.findtext("shuffleanswers")),
            },
            answers=answers,
        )
