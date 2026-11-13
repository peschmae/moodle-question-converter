"""Question type handlers: one module per Moodle question type."""

from __future__ import annotations

from moodle_qc.qtypes.base import QuestionType
from moodle_qc.qtypes.ddwtos import DragAndDropIntoText
from moodle_qc.qtypes.judgement import KPrime, MultipleTrueFalse
from moodle_qc.qtypes.multichoice import MultiChoice
from moodle_qc.qtypes.sc import SingleChoice

HANDLERS: dict[str, QuestionType] = {
    handler.name: handler
    for handler in (
        SingleChoice(),
        MultiChoice(),
        KPrime(),
        MultipleTrueFalse(),
        DragAndDropIntoText(),
    )
}
"""Supported question types by Moodle type name."""


def handler_for(qtype: str) -> QuestionType | None:
    return HANDLERS.get(qtype)
