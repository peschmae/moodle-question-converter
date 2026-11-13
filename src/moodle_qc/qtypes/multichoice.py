"""``multichoice``: Moodle's multiple choice, with radio buttons (one answer) or checkboxes."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from moodle_qc.qtypes.base import ReadResult, add_field, flag, read_field, read_flag, text_of
from moodle_qc.question import Question, Render, ToMarkdown
from moodle_qc.source import Answer
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


def default_fractions(answers: list[Answer], multiple: bool) -> list[float]:
    """Percentages without overrides: single → 100/0; multiple → correct answers share 100,
    wrong answers deduct the same share."""
    correct = sum(answer.correct for answer in answers)
    if not multiple:
        return [100.0 if answer.correct else 0.0 for answer in answers]
    share = 100.0 / correct if correct else 0.0
    return [share if answer.correct else -share for answer in answers]


def fractions(answers: list[Answer], multiple: bool) -> list[float]:
    defaults = default_fractions(answers, multiple)
    return [
        answer.fraction if answer.fraction is not None else default
        for answer, default in zip(answers, defaults, strict=True)
    ]


def format_fraction(value: float) -> str:
    return f"{round(value, 5):.5f}".rstrip("0").rstrip(".")


def valid_grade(value: float) -> bool:
    return any(abs(abs(value) - option) < _TOLERANCE for option in GRADE_OPTIONS)


class MultiChoice:
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

    def read(self, element: ET.Element, text: str, to_markdown: ToMarkdown) -> ReadResult:
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
        for answer, value, default in zip(
            answers, values, default_fractions(answers, multiple), strict=True
        ):
            if abs(value - default) > _TOLERANCE:
                answer.fraction = float(format_fraction(value))
        settings: dict[str, object] = {
            "shuffle": read_flag(element.findtext("shuffleanswers")),
            "numbering": (element.findtext("answernumbering") or "abc").strip(),
            "show_instruction": text_of(element, "showstandardinstruction") == "1",
        }
        if multiple != is_multiple(answers, None):
            settings["multiple"] = multiple
        return ReadResult(settings=settings, answers=answers)
