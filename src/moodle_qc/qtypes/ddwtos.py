"""``ddwtos``: drag and drop into text.

In a question source, gaps are written inline with their correct word and gap group,
``[[word|group]]`` (also inside code blocks); ``[[word]]`` belongs to the unnamed group.
Distractors are listed per gap group in the front matter::

    distractors:
      keyword: [expr, keep_firing_for]
      function: [irate]
    reusable: [keyword]

Moodle numbers everything: the text holds ``[[n]]`` (n = position of the dragbox), each
``<dragbox>`` has a ``<group>`` number. Gap groups are numbered in the order of the
``distractors`` mapping, then in order of first use; dragboxes list the correct words in gap
order, then the distractors group by group.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from moodle_qc.qtypes.base import BaseQuestionType, ReadResult, read_flag
from moodle_qc.question import Question, Render, ToMarkdown
from moodle_qc.source import SourceDocument
from moodle_qc.xmlnode import Node

UNNAMED = ""

_GAP = re.compile(r"\[\[([^\[\]|]+?)(?:\|([^\[\]|]+?))?\]\]")
_NUMBERED_GAP = re.compile(r"\[\[(\d+)\]\]")


@dataclass
class Dragbox:
    word: str
    group: str
    reusable: bool = False


@dataclass
class GapLayout:
    """How the gaps of a question source map to Moodle's numbered dragboxes and groups."""

    text: str
    """Question text with ``[[n]]`` markers."""
    groups: list[str]
    """Gap group names; group number = index + 1."""
    dragboxes: list[Dragbox] = field(default_factory=list)
    gaps: list[tuple[str, str]] = field(default_factory=list)
    """(word, group) of every gap, in text order."""


def distractors_by_group(setting: Any) -> dict[str, list[str]]:
    if setting is None:
        return {}
    if isinstance(setting, list):
        return {UNNAMED: [str(word) for word in setting]}
    if isinstance(setting, dict):
        return {
            str(group): [str(word) for word in (words or [])] for group, words in setting.items()
        }
    raise ValueError("distractors must be a list of words or a mapping of gap group → words")


def reusable_groups(setting: Any) -> set[str]:
    if setting is True:
        return {UNNAMED}
    if isinstance(setting, list):
        return {str(group) for group in setting}
    return set()


def layout(text: str, settings: dict[str, Any]) -> GapLayout:
    distractors = distractors_by_group(settings.get("distractors"))
    reusable = reusable_groups(settings.get("reusable"))
    groups = list(distractors)
    gaps = [(match.group(1), match.group(2) or UNNAMED) for match in _GAP.finditer(text)]
    for _, group in gaps:
        if group not in groups:
            groups.append(group)

    result = GapLayout(text="", groups=groups, gaps=gaps)
    numbers: dict[tuple[str, str], int] = {}

    def number_gap(match: re.Match[str]) -> str:
        key = (match.group(1), match.group(2) or UNNAMED)
        if key in numbers and key[1] in reusable:
            return f"[[{numbers[key]}]]"
        result.dragboxes.append(Dragbox(key[0], key[1], key[1] in reusable))
        numbers[key] = len(result.dragboxes)
        return f"[[{numbers[key]}]]"

    result.text = _GAP.sub(number_gap, text)
    for group, words in distractors.items():
        result.dragboxes.extend(Dragbox(word, group, group in reusable) for word in words)
    return result


class DragAndDropIntoText(BaseQuestionType):
    name = "ddwtos"
    front_matter_keys = frozenset({"distractors", "reusable"})
    has_answers = False
    combined_feedback = True

    def validate(self, question: Question) -> list[str]:
        try:
            gaps = layout(question.document.text, question.settings)
        except ValueError as error:
            return [str(error)]
        problems: list[str] = []
        if not gaps.gaps:
            problems.append("has no gaps; write them as [[word|group]] in the question text")
        reusable = reusable_groups(question.settings.get("reusable"))
        used = {group for _, group in gaps.gaps}
        for group in gaps.groups:
            label = f"gap group {group!r}" if group else "the gaps"
            words = [box.word for box in gaps.dragboxes if box.group == group]
            correct = {word for word, gap_group in gaps.gaps if gap_group == group}
            if group not in used:
                problems.append(f"{label} has distractors but no gap uses it")
            elif not set(words) - correct:
                problems.append(f"{label} has no distractor")
            duplicates = sorted({w for w in words if words.count(w) > 1})
            if duplicates and group not in reusable:
                problems.append(f"{label} has the word(s) {', '.join(duplicates)} more than once")
        unknown = reusable - set(gaps.groups)
        if unknown:
            problems.append(f"reusable names unknown gap group(s): {', '.join(sorted(unknown))}")
        return problems

    def question_text(self, question: Question) -> str:
        return layout(question.document.text, question.settings).text

    def write(self, question: Question, node: Node, render: Render) -> None:
        gaps = layout(question.document.text, question.settings)
        node.add("shuffleanswers", "1" if question.settings["shuffle"] else "0")
        for box in gaps.dragboxes:
            dragbox = node.add("dragbox")
            dragbox.add("text", box.word)
            dragbox.add("group", str(gaps.groups.index(box.group) + 1))
            if box.reusable:
                dragbox.add("infinite")

    def read(
        self,
        element: ET.Element,
        text: str,
        to_markdown: ToMarkdown,
        existing: SourceDocument | None = None,
    ) -> ReadResult:
        boxes = [
            (
                (box.findtext("text") or "").strip(),
                int((box.findtext("group") or "1").strip()),
                box.find("infinite") is not None,
            )
            for box in element.findall("dragbox")
        ]
        group_numbers = sorted({group for _, group, _ in boxes})
        names = _group_names(group_numbers, existing)

        used: set[int] = set()

        def word_gap(match: re.Match[str]) -> str:
            index = int(match.group(1)) - 1
            if not 0 <= index < len(boxes):
                return match.group(0)
            used.add(index)
            word, group, _ = boxes[index]
            name = names[group]
            return f"[[{word}|{name}]]" if name else f"[[{word}]]"

        gap_text = _NUMBERED_GAP.sub(word_gap, text)
        distractors: dict[str, list[str]] = {}
        for index, (word, group, _) in enumerate(boxes):
            if index not in used:
                distractors.setdefault(names[group], []).append(word)
        ordered = {
            names[n]: distractors[names[n]] for n in group_numbers if names[n] in distractors
        }
        settings: dict[str, Any] = {"shuffle": read_flag(element.findtext("shuffleanswers"))}
        if ordered:
            settings["distractors"] = ordered[UNNAMED] if list(ordered) == [UNNAMED] else ordered
        reusable = [names[n] for n in group_numbers if any(g == n and inf for _, g, inf in boxes)]
        if reusable:
            settings["reusable"] = True if reusable == [UNNAMED] else reusable
        return ReadResult(settings=settings, text=gap_text)


def _group_names(numbers: list[int], existing: SourceDocument | None) -> dict[int, str]:
    """Names for Moodle's group numbers: from the question source being overwritten if it has
    the same groups, else ``group1``, ``group2``, … (unnamed if there is only one group)."""
    if existing is not None:
        try:
            known = layout(existing.text, existing.front_matter).groups
        except ValueError:
            known = []
        if len(known) == len(numbers):
            return dict(zip(numbers, known, strict=True))
    if len(numbers) == 1:
        return {numbers[0]: UNNAMED}
    return {number: f"group{number}" for number in numbers}
