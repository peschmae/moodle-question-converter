"""Question sources → questions → Moodle XML import file."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from moodle_qc.collection import Collection
from moodle_qc.errors import UserError
from moodle_qc.markdown import render
from moodle_qc.naming import category_path, question_id_from_path
from moodle_qc.qtypes import handler_for
from moodle_qc.qtypes.base import QuestionType, add_field, flag
from moodle_qc.question import Question, RenderedText
from moodle_qc.source import parse_source
from moodle_qc.xmlnode import Node, serialize


def load_question(collection: Collection, path: Path) -> Question:
    """Read a question source and resolve its settings, question name, ID and category."""
    relative = collection.relative(path)
    origin = relative.as_posix()
    document = parse_source(path.read_text(encoding="utf-8"), origin)
    front_matter = document.front_matter
    qtype = front_matter.get("type")
    if not qtype:
        raise UserError(f"{origin}: front matter has no question type (type: …).")
    qtype = str(qtype)
    name = str(front_matter.get("name") or document.title or path.stem)
    question_id = str(front_matter.get("id") or question_id_from_path(relative))
    category = str(
        front_matter.get("category") or category_path(relative.parent, collection.root_category)
    ).strip("/")
    return Question(
        qtype=qtype,
        name=name,
        question_id=question_id,
        category=category,
        document=document,
        settings=collection.settings_for(qtype, front_matter),
        origin=origin,
        folder=path.parent,
    )


def require_handler(question: Question) -> QuestionType:
    handler = handler_for(question.qtype)
    if handler is None:
        raise UserError(f"{question.origin}: unsupported question type {question.qtype!r}.")
    return handler


def question_node(question: Question, collection: Collection) -> Node:
    """The ``<question>`` element of a question."""
    handler = require_handler(question)
    settings = question.settings

    def render_field(markdown: str) -> RenderedText:
        return RenderedText(render(markdown, pre_style=collection.pre_style))

    node = Node("question", {"type": question.qtype})
    node.add_text("name", question.name)
    add_field(node, "questiontext", question.document.text, render_field)
    add_field(node, "generalfeedback", question.document.solution, render_field)
    node.add("defaultgrade", _number(settings["points"]))
    node.add("penalty", _number(settings["penalty"]))
    node.add("hidden", "0")
    node.add("idnumber", question.question_id)
    handler.write(question, node, render_field)
    if handler.combined_feedback:
        feedback = settings.get("feedback") or {}
        for key, tag in (
            ("correct", "correctfeedback"),
            ("partially", "partiallycorrectfeedback"),
            ("incorrect", "incorrectfeedback"),
        ):
            add_field(node, tag, str(feedback.get(key) or ""), render_field)
        if settings.get("show_num_correct"):
            node.add("shownumcorrect")
    tags = settings.get("tags") or []
    if tags:
        tags_node = node.add("tags")
        for tag in tags:
            tags_node.add_text("tag", str(tag))
    return node


def import_file(collection: Collection, questions: Iterable[Question]) -> str:
    """The Moodle XML import file for the questions, each category entry before its questions."""
    quiz = Node("quiz")
    current_category: str | None = None
    for question in questions:
        if question.category != current_category:
            current_category = question.category
            if current_category:
                entry = quiz.add("question", type="category")
                entry.add_text("category", current_category)
                entry.add_text("info", "", format="html")
        quiz.children.append(question_node(question, collection))
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + serialize(quiz)


def _number(value: object) -> str:
    if isinstance(value, bool):
        return flag(value)
    if isinstance(value, int | float):
        return f"{float(value):.7f}".rstrip("0").rstrip(".")
    return str(value)
