"""``kprime`` and ``mtf`` (ETH plugins): each answer is judged true or false.

Rows are the answers, columns the judgement labels; the correct judgement of a row is the column
whose ``<weight>`` is greater than 0.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from moodle_qc.qtypes.base import (
    BaseQuestionType,
    ReadResult,
    add_field,
    flag,
    read_field,
    read_flag,
    text_of,
)
from moodle_qc.question import Question, Render, ToMarkdown
from moodle_qc.source import Answer, SourceDocument
from moodle_qc.xmlnode import Node


class _Judgement(BaseQuestionType):
    name: str
    scoring_methods: tuple[str, ...]
    front_matter_keys = frozenset({"scoring", "labels"})
    has_answers = True
    combined_feedback = False

    def validate(self, question: Question) -> list[str]:
        problems: list[str] = []
        if question.settings.get("scoring") not in self.scoring_methods:
            problems.append(f"scoring must be one of {', '.join(self.scoring_methods)}")
        labels = question.settings.get("labels")
        if not isinstance(labels, list) or len(labels) != 2 or not all(labels):
            problems.append("labels must be two judgement labels, e.g. [richtig, falsch]")
        if not question.answers:
            problems.append("needs at least one answer")
        return problems

    def write(self, question: Question, node: Node, render: Render) -> None:
        settings = question.settings
        answers = question.answers
        node.add_text("scoringmethod", str(settings["scoring"]))
        node.add("shuffleanswers", flag(settings["shuffle"]))
        node.add("numberofrows", str(len(answers)))
        node.add("numberofcolumns", "2")
        self._write_extra(settings, node)
        for number, answer in enumerate(answers, 1):
            row = node.add("row", number=str(number))
            add_field(row, "optiontext", answer.text, render)
            add_field(row, "feedbacktext", answer.feedback, render)
        for number, label in enumerate(settings["labels"], 1):
            column = node.add("column", number=str(number))
            column.add_text("responsetext", str(label), format="moodle_auto_format")
        for row_number, answer in enumerate(answers, 1):
            for column_number in (1, 2):
                weight = node.add(
                    "weight", rownumber=str(row_number), columnnumber=str(column_number)
                )
                is_set = answer.correct == (column_number == 1)
                weight.add("value", "1.000" if is_set else "0.000")

    def _write_extra(self, settings: dict[str, Any], node: Node) -> None:
        """Elements only one of the two types has."""

    def read(
        self,
        element: ET.Element,
        text: str,
        to_markdown: ToMarkdown,
        existing: SourceDocument | None = None,
    ) -> ReadResult:
        weights = {
            (weight.get("rownumber"), weight.get("columnnumber")): float(
                text_of(weight, "value") or 0
            )
            for weight in element.findall("weight")
        }
        answers = [
            Answer(
                read_field(row.find("optiontext"), to_markdown),
                weights.get((row.get("number"), "1"), 0) > 0,
                read_field(row.find("feedbacktext"), to_markdown),
            )
            for row in sorted(element.findall("row"), key=lambda r: int(r.get("number", "0")))
        ]
        columns = sorted(element.findall("column"), key=lambda c: int(c.get("number", "0")))
        settings: dict[str, Any] = {
            "scoring": text_of(element, "scoringmethod"),
            "shuffle": read_flag(element.findtext("shuffleanswers")),
            "labels": [text_of(column, "responsetext") for column in columns],
        }
        settings.update(self._read_extra(element))
        return ReadResult(settings=settings, answers=answers)

    def _read_extra(self, element: ET.Element) -> dict[str, Any]:
        return {}


class KPrime(_Judgement):
    name = "kprime"
    scoring_methods = ("kprime", "kprimeonezero", "subpoints")

    def validate(self, question: Question) -> list[str]:
        problems = super().validate(question)
        if question.answers and len(question.answers) != 4:
            problems.append(f"needs exactly four answers, has {len(question.answers)}")
        return problems


class MultipleTrueFalse(_Judgement):
    name = "mtf"
    scoring_methods = ("subpoints", "mtfonezero", "subpointdeduction")
    front_matter_keys = frozenset({"scoring", "labels", "numbering", "deduction"})

    def validate(self, question: Question) -> list[str]:
        problems = super().validate(question)
        deduction = question.settings.get("deduction")
        if not isinstance(deduction, int | float) or isinstance(deduction, bool) or deduction < 0:
            problems.append("deduction must be a number of at least 0")
        return problems

    def _write_extra(self, settings: dict[str, Any], node: Node) -> None:
        node.add("answernumbering", str(settings["numbering"]))
        deduction = float(settings["deduction"])
        node.add("deduction", f"{deduction:g}")

    def _read_extra(self, element: ET.Element) -> dict[str, Any]:
        deduction = float(text_of(element, "deduction") or 0)
        return {
            "numbering": text_of(element, "answernumbering") or "none",
            "deduction": int(deduction) if deduction.is_integer() else deduction,
        }
