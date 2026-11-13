"""A local HTML page showing questions roughly as Moodle would, for review without importing."""

from __future__ import annotations

import base64
import html
import mimetypes
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from moodle_qc.collection import Collection
from moodle_qc.markdown import is_external, render
from moodle_qc.qtypes import RAW, handler_for
from moodle_qc.qtypes.ddwtos import layout
from moodle_qc.qtypes.multichoice import format_fraction, fractions, is_multiple
from moodle_qc.question import Question
from moodle_qc.validate import Problem

_NUMBERED_GAP = re.compile(r"\[\[(\d+)\]\]")

_STYLE = """
body { font-family: system-ui, sans-serif; max-width: 52rem; margin: 2rem auto; padding: 0 1rem;
       color: #1d2125; background: #f5f6f8; }
h1 { font-size: 1.4rem; }
.problems { background: #fdecea; border: 1px solid #f5c2c0; padding: .5rem 1rem;
            border-radius: 6px; }
.question { background: #fff; border: 1px solid #dee2e6; border-radius: 6px; padding: 1rem 1.25rem;
            margin: 1rem 0; }
.meta { color: #6a737b; font-size: .85rem; margin-bottom: .5rem; }
.question h2 { font-size: 1.1rem; margin: 0 0 .25rem; }
.answers { list-style: none; padding: 0; }
.answers li { border: 1px solid #dee2e6; border-radius: 4px; padding: .4rem .6rem;
              margin: .3rem 0; }
.answers li.correct { border-color: #3a8a3a; background: #eef7ee; }
.answers .mark { font-weight: 600; margin-right: .4rem; }
.answers .feedback { color: #6a737b; font-size: .9rem; }
.gap { display: inline-block; min-width: 4rem; border: 1px dashed #0f6cbf; background: #e7f1fa;
       padding: 0 .3rem; border-radius: 3px; }
.distractors { color: #6a737b; font-size: .9rem; }
.solution { border-left: 4px solid #f0ad4e; background: #fff8ec; padding: .5rem 1rem;
            margin-top: 1rem; }
.solution-title { font-weight: 600; font-size: .85rem; text-transform: uppercase; color: #8a5a00; }
pre { background: #f8f9fa; padding: .5rem; overflow-x: auto; }
img { max-width: 100%; }
"""


def preview_page(
    collection: Collection, questions: Sequence[Question], problems: Sequence[Problem]
) -> str:
    sections = [_question_section(collection, question) for question in questions]
    problem_list = ""
    if problems:
        items = "".join(f"<li>{html.escape(str(problem))}</li>" for problem in problems)
        problem_list = f'<div class="problems"><strong>Problems</strong><ul>{items}</ul></div>'
    return (
        '<!DOCTYPE html>\n<html lang="de"><head><meta charset="utf-8">'
        f"<title>moodle-qc preview</title><style>{_STYLE}</style></head><body>"
        f"<h1>Preview: {len(questions)} question(s)</h1>{problem_list}"
        + "".join(sections)
        + "</body></html>\n"
    )


def _question_section(collection: Collection, question: Question) -> str:
    handler = handler_for(question.qtype)

    def md(markdown: str) -> str:
        return render(
            markdown,
            pre_style=collection.pre_style,
            image_src=lambda path: _data_uri(question.folder, path),
        )

    meta = " · ".join(
        html.escape(part)
        for part in (question.qtype, question.category or "(no category)", question.question_id)
    )
    body: str
    if handler is RAW:
        inner = RAW.inner_type(question) or "?"
        body = f"<p><em>Raw question source ({html.escape(inner)}) – not rendered.</em></p>"
    elif question.qtype == "ddwtos":
        body = _gap_text(question, md)
    else:
        body = md(question.document.text) + _answers(question, md)
    solution = ""
    if question.document.solution:
        solution = (
            '<div class="solution"><div class="solution-title">Solution</div>'
            f"{md(question.document.solution)}</div>"
        )
    return (
        f'<section class="question"><div class="meta">{meta}</div>'
        f"<h2>{html.escape(question.name)}</h2>{body}{solution}</section>"
    )


def _answers(question: Question, render_md: Callable[[str], str]) -> str:
    answers = question.answers
    labels = ["✓", "✗"]
    percentages: list[str] = []
    if question.qtype in {"kprime", "mtf"}:
        labels = [str(label) for label in question.settings.get("labels", labels)]
    if question.qtype == "multichoice":
        multiple = is_multiple(answers, question.settings.get("multiple"))
        percentages = [f"{format_fraction(v)}%" for v in fractions(answers, multiple)]
    items = []
    for index, answer in enumerate(answers):
        mark = labels[0] if answer.correct else labels[1]
        if question.qtype in {"sc", "multichoice"}:
            mark = "✓" if answer.correct else "○"
        if percentages:
            mark += f" {percentages[index]}"
        feedback = (
            f'<div class="feedback">{render_md(answer.feedback)}</div>' if answer.feedback else ""
        )
        css = ' class="correct"' if answer.correct else ""
        items.append(
            f'<li{css}><span class="mark">{html.escape(mark)}</span>'
            f"{render_md(answer.text)}{feedback}</li>"
        )
    return f'<ul class="answers">{"".join(items)}</ul>'


def _gap_text(question: Question, render_md: Callable[[str], str]) -> str:
    try:
        gaps = layout(question.document.text, question.settings)
    except ValueError as error:
        return f"<p>{html.escape(str(error))}</p>"

    def gap(match: re.Match[str]) -> str:
        index = int(match.group(1)) - 1
        word = gaps.dragboxes[index].word if 0 <= index < len(gaps.dragboxes) else "?"
        return f'<span class="gap">{html.escape(word)}</span>'

    text = _NUMBERED_GAP.sub(gap, render_md(gaps.text))
    correct = {(word, group) for word, group in gaps.gaps}
    lines = []
    for group in gaps.groups:
        words = [
            b.word for b in gaps.dragboxes if b.group == group and (b.word, group) not in correct
        ]
        if words:
            label = html.escape(group) if group else "Distractors"
            lines.append(f"<li><strong>{label}</strong>: {html.escape(', '.join(words))}</li>")
    distractors = f'<ul class="distractors">{"".join(lines)}</ul>' if lines else ""
    return text + distractors


def _data_uri(folder: Path | None, path: str) -> str:
    if folder is None or is_external(path):
        return path
    file = folder / path
    if not file.is_file():
        return path
    mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(file.read_bytes()).decode('ascii')}"
