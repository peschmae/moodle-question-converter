"""Validation of question sources, shared by ``check`` and ``generate``."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from moodle_qc.collection import Collection
from moodle_qc.convert import load_question
from moodle_qc.errors import UserError
from moodle_qc.qtypes import RAW, handler_for
from moodle_qc.question import COMMON_FRONT_MATTER, Question

COMBINED_FEEDBACK_KEYS = frozenset({"show_num_correct"})


@dataclass(frozen=True)
class Problem:
    origin: str
    """The question source (path relative to the collection root)."""
    message: str

    def __str__(self) -> str:
        return f"{self.origin}: {self.message}"


@dataclass
class Validated:
    questions: list[Question]
    problems: list[Problem]


def validate(collection: Collection, paths: Sequence[Path]) -> Validated:
    """Load and check the selected question sources."""
    questions: list[Question] = []
    problems: list[Problem] = []
    for path in collection.sources(paths):
        origin = collection.relative(path).as_posix()
        try:
            question = load_question(collection, path)
        except UserError as error:
            message = str(error).removeprefix(f"{origin}: ")
            problems.append(Problem(origin, message))
            continue
        questions.append(question)
        problems.extend(
            Problem(origin, message) for message in _question_problems(collection, question)
        )

    by_id: dict[str, list[str]] = defaultdict(list)
    for question in questions:
        by_id[question.question_id].append(question.origin)
    for question_id, origins in by_id.items():
        if len(origins) > 1:
            for origin in origins:
                others = ", ".join(o for o in origins if o != origin)
                problems.append(
                    Problem(origin, f"question ID {question_id!r} is also used by {others}")
                )
    problems.sort(key=lambda p: p.origin)
    return Validated(questions, problems)


def _question_problems(collection: Collection, question: Question) -> list[str]:
    handler = handler_for(question.qtype)
    moodle_type = RAW.inner_type(question) if handler is RAW else question.qtype
    allowed = collection.allowed_types
    if allowed is not None and moodle_type is not None and moodle_type not in allowed:
        return [
            f"question type {moodle_type!r} is not allowed by the collection config "
            f"(allowed: {', '.join(sorted(allowed))})"
        ]
    if handler is None:
        return [f"unsupported question type {question.qtype!r}"]
    problems: list[str] = []
    known = COMMON_FRONT_MATTER | handler.front_matter_keys
    if handler.combined_feedback:
        known |= COMBINED_FEEDBACK_KEYS
    unknown = sorted(set(question.document.front_matter) - known)
    if unknown:
        problems.append(f"unknown front matter key(s): {', '.join(unknown)}")
    if handler.has_answers and question.document.answers is None:
        problems.append("has no '## Answers' section")
    points = question.settings.get("points")
    if not isinstance(points, int | float) or isinstance(points, bool) or points <= 0:
        problems.append("points must be a positive number")
    penalty = question.settings.get("penalty")
    if not isinstance(penalty, int | float) or isinstance(penalty, bool) or not 0 <= penalty <= 1:
        problems.append("penalty must be a number between 0 and 1")
    if handler.has_answers and question.document.answers is None:
        return problems
    return problems + handler.validate(question)
