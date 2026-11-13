"""A question resolved from its question source and the collection config."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moodle_qc.source import Answer, SourceDocument

COMMON_FRONT_MATTER = frozenset(
    {"type", "id", "name", "category", "lang", "points", "penalty", "shuffle", "tags", "feedback"}
)
"""Front matter keys every question type accepts."""


@dataclass
class Question:
    qtype: str
    name: str
    question_id: str
    category: str
    document: SourceDocument
    settings: dict[str, Any]
    origin: str
    """Where the question came from, for messages (path relative to the collection root)."""
    folder: Path | None = None
    """Folder of the question source, for resolving relative image paths."""

    @property
    def answers(self) -> list[Answer]:
        return self.document.answers or []


@dataclass
class EmbeddedFile:
    name: str
    content: bytes


@dataclass
class RenderedText:
    html: str
    files: list[EmbeddedFile] = field(default_factory=list)


Render = Callable[[str], RenderedText]
"""Renders Markdown of one field to HTML, collecting embedded images."""

ToMarkdown = Callable[[str, dict[str, bytes]], str]
"""Converts the HTML of one field (with its embedded files by name) to Markdown."""
