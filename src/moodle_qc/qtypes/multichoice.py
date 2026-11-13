"""``multichoice``: Moodle's multiple choice, with radio buttons (one answer) or checkboxes."""

from __future__ import annotations

import xml.etree.ElementTree as ET

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

NUMBERING = ("abc", "ABCD", "123", "iii", "IIII", "none")

GRADE_OPTIONS = (
    100, 90, 83.33333, 80, 75, 70, 66.66667, 60, 50, 40, 33.33333, 30, 25, 20,
    16.66667, 14.28571, 12.5, 11.11111, 10, 5, 0,
)  # fmt: skip
"""Percentages Moodle accepts for an answer (also negated)."""

_TOLERANCE = 0.0001


def is_multiple(answers: list[Answer], setting: object) -> bool:
    """Checkboxes if set explicitly, otherwise if more than one answer is correct."""
    if isinstance(setting, bool):
        return setting
    return sum(answer.correct for answer in answers) != 1


def fractions(answers: list[Answer], multiple: bool) -> list[float]:
    """Percentages of the answers. Single: correct 100, wrong 0. Multiple: correct answers
    without an explicit percentage share what the explicit ones leave of 100 %, wrong answers
    deduct 100 % divided by the number of correct answers. Explicit ``{n%}`` always wins."""
    correct = [answer for answer in answers if answer.correct]
    if not multiple:
        defaults = {True: 100.0, False: 0.0}
    else:
        fixed = sum(a.fraction for a in correct if a.fraction is not None)
        free = sum(1 for a in correct if a.fraction is None)
        defaults = {
            True: (100.0 - fixed) / free if free else 0.0,
            False: -100.0 / len(correct) if correct else 0.0,
        }
    return [
        answer.fraction if answer.fraction is not None else defaults[answer.correct]
        for answer in answers
    ]


def explicit_fractions(values: list[float], multiple: bool) -> list[float | None]:
    """The inverse of ``fractions``: which percentages must be written as ``{n%}``."""
    correct = [v for v in values if v > 0]
    explicit: list[float | None] = [None] * len(values)
    if not multiple:
        for index, value in enumerate(values):
            if abs(value - (100.0 if value > 0 else 0.0)) > _TOLERANCE:
                explicit[index] = value
        return explicit
    # The free share is the most common correct percentage, if the others leave exactly it.
    free_share = max(set(correct), key=lambda v: (correct.count(v), v)) if correct else 0.0
    others = [v for v in correct if abs(v - free_share) > _TOLERANCE]
    free = len(correct) - len(others)
    if not free or abs((100.0 - sum(others)) / free - free_share) > _TOLERANCE:
        free_share = float("nan")  # no consistent free share: every correct answer is explicit
    deduction = -100.0 / len(correct) if correct else 0.0
    for index, value in enumerate(values):
        default = free_share if value > 0 else deduction
        if not abs(value - default) <= _TOLERANCE:  # also true when default is nan
            explicit[index] = value
    return explicit


def format_fraction(value: float) -> str:
    return f"{round(value, 5):.5f}".rstrip("0").rstrip(".")


def valid_grade(value: float) -> bool:
    return any(abs(abs(value) - option) < _TOLERANCE for option in GRADE_OPTIONS)


class MultiChoice(BaseQuestionType):
    name = "multichoice"
    front_matter_keys = frozenset({"multiple", "numbering", "show_instruction"})
    has_answers = True
    combined_feedback = True

    def validate(self, question: Question) -> list[str]:
        answers = question.answers
        problems: list[str] = []
        if not any(answer.correct for answer in answers):
            problems.append("needs at least one correct answer ([x])")
            return problems
        multiple_setting = question.settings.get("multiple")
        if multiple_setting is not None and not isinstance(multiple_setting, bool):
            problems.append("multiple must be true or false")
        multiple = is_multiple(answers, multiple_setting)
        for number, value in enumerate(fractions(answers, multiple), 1):
            if not valid_grade(value):
                problems.append(
                    f"answer {number} gets {format_fraction(value)}%, which Moodle doesn't accept; "
                    "set the percentages explicitly ({…%})"
                )
        if multiple:
            total = sum(v for v in fractions(answers, multiple) if v > 0)
            if abs(total - 100) > 0.01:
                problems.append(
                    f"the correct answers add up to {format_fraction(total)}%, not 100%"
                )
        if question.settings.get("numbering") not in NUMBERING:
            problems.append(f"numbering must be one of {', '.join(NUMBERING)}")
        return problems

    def write(self, question: Question, node: Node, render: Render) -> None:
        settings = question.settings
        answers = question.answers
        multiple = is_multiple(answers, settings.get("multiple"))
        node.add("single", flag(not multiple))
        node.add("shuffleanswers", flag(settings["shuffle"]))
        node.add("answernumbering", str(settings["numbering"]))
        node.add("showstandardinstruction", "1" if settings.get("show_instruction") else "0")
        for answer, value in zip(answers, fractions(answers, multiple), strict=True):
            element = add_field(node, "answer", answer.text, render)
            element.attrs = {"fraction": format_fraction(value), "format": "html"}
            add_field(element, "feedback", answer.feedback, render)

    def read(
        self,
        element: ET.Element,
        text: str,
        to_markdown: ToMarkdown,
        existing: SourceDocument | None = None,
    ) -> ReadResult:
        values: list[float] = []
        answers: list[Answer] = []
        for answer_element in element.findall("answer"):
            value = float(answer_element.get("fraction", "0"))
            values.append(value)
            answers.append(
                Answer(
                    read_field(answer_element, to_markdown),
                    value > 0,
                    read_field(answer_element.find("feedback"), to_markdown),
                )
            )
        multiple = not read_flag(element.findtext("single"), default=True)
        for answer, explicit in zip(answers, explicit_fractions(values, multiple), strict=True):
            if explicit is not None:
                answer.fraction = _plain(float(format_fraction(explicit)))
        settings: dict[str, object] = {
            "shuffle": read_flag(element.findtext("shuffleanswers")),
            "numbering": (element.findtext("answernumbering") or "abc").strip(),
            "show_instruction": text_of(element, "showstandardinstruction") == "1",
        }
        if multiple != is_multiple(answers, None):
            settings["multiple"] = multiple
        return ReadResult(settings=settings, answers=answers)


def _plain(value: float) -> float | int:
    return int(value) if value.is_integer() else value
