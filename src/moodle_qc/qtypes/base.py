"""The interface every question type handler implements, plus helpers shared by handlers."""

from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Protocol

from moodle_qc.question import Question, Render, ToMarkdown
from moodle_qc.source import Answer, SourceDocument
from moodle_qc.xmlnode import Node


@dataclass
class ReadResult:
    """What a handler reads from a Moodle question element besides the common header."""

    settings: dict[str, Any] = field(default_factory=dict)
    """Type-specific settings as front matter (written only where they differ from defaults)."""
    answers: list[Answer] | None = None
    text: str | None = None
    """Replacement question text in Markdown (e.g. ``ddwtos`` puts its gaps back in)."""


class QuestionType(Protocol):
    name: str
    """Moodle's question type name, e.g. ``sc``."""
    front_matter_keys: frozenset[str]
    """Type-specific front matter keys (in addition to the common ones)."""
    has_answers: bool
    """Whether question sources of this type have an ``## Answers`` section."""
    combined_feedback: bool
    """Whether the type writes Moodle's correct/partially/incorrect feedback."""

    def validate(self, question: Question) -> list[str]:
        """Problems with the question, as messages (empty if valid)."""
        ...

    def write(self, question: Question, node: Node, render: Render) -> None:
        """Add the type-specific elements to the ``<question>`` node."""
        ...

    def question_text(self, question: Question) -> str:
        """The question text (Markdown) as written to Moodle."""
        ...

    def read(
        self,
        element: ET.Element,
        text: str,
        to_markdown: ToMarkdown,
        existing: SourceDocument | None = None,
    ) -> ReadResult:
        """Read the type-specific elements; ``text`` is the question text already in Markdown,
        ``existing`` the question source being overwritten (if any)."""
        ...


class BaseQuestionType:
    """Defaults for handlers."""

    def question_text(self, question: Question) -> str:
        return question.document.text


def add_field(node: Node, tag: str, markdown: str, render: Render, **attrs: str) -> Node:
    """Add a Moodle HTML text field (``<tag format="html"><text>…</text>[<file>…]</tag>``)."""
    rendered = render(markdown) if markdown else None
    child = node.add_text(tag, rendered.html if rendered else "", format="html", **attrs)
    for embedded in rendered.files if rendered else []:
        child.add(
            "file",
            base64.b64encode(embedded.content).decode("ascii"),
            name=embedded.name,
            path="/",
            encoding="base64",
        )
    return child


def read_field(element: ET.Element | None, to_markdown: ToMarkdown) -> str:
    """Markdown of a Moodle HTML text field, with its embedded files."""
    if element is None:
        return ""
    html = element.findtext("text", default="") or ""
    if not html.strip():
        return ""
    files = {
        file.get("name", ""): base64.b64decode(file.text or "")
        for file in element.findall("file")
        if file.get("name")
    }
    return to_markdown(html, files)


def flag(value: object) -> str:
    return "true" if value else "false"


def read_flag(text: str | None, default: bool = True) -> bool:
    if text is None:
        return default
    return text.strip().lower() in {"1", "true", "yes"}


def text_of(element: ET.Element, path: str, default: str = "") -> str:
    """Text of a child element (also inside ``<text>``), stripped."""
    found = element.find(path)
    if found is None:
        return default
    inner = found.find("text")
    return ((inner.text if inner is not None else found.text) or "").strip()
