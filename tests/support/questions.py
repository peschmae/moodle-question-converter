"""Build questions in memory for handler unit tests."""

from typing import Any

from moodle_qc.collection import BUILTIN_DEFAULTS, BUILTIN_TYPE_DEFAULTS, merge_settings
from moodle_qc.question import Question
from moodle_qc.source import Answer, SourceDocument


def question(qtype: str, *answers: Answer, text: str = "Text", **settings: Any) -> Question:
    return Question(
        qtype=qtype,
        name="Q",
        question_id="q",
        category="",
        document=SourceDocument(text=text, answers=list(answers)),
        settings=merge_settings(BUILTIN_DEFAULTS, BUILTIN_TYPE_DEFAULTS[qtype], settings),
        origin="q.md",
    )


def answers(*correct: bool) -> list[Answer]:
    return [Answer(f"Antwort {number}", flag) for number, flag in enumerate(correct, 1)]
