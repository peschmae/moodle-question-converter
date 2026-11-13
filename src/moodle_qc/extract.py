"""Moodle export → question sources inside a question collection."""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from moodle_qc.collection import Collection
from moodle_qc.convert import load_question
from moodle_qc.errors import UserError
from moodle_qc.markdown import to_markdown
from moodle_qc.moodle_xml import ExportedQuestion, read_export
from moodle_qc.naming import (
    folder_for_category,
    question_id_from_category,
    question_id_from_path,
    slug,
)
from moodle_qc.qtypes import handler_for
from moodle_qc.qtypes.base import QuestionType, read_field, text_of
from moodle_qc.source import SourceDocument, format_source, parse_source

KEPT_FROM_EXISTING = ("id", "name", "category", "lang")
"""Front matter a Moodle export can't tell us; kept when a question source is overwritten."""


@dataclass
class ExtractedSource:
    path: Path
    content: str
    replaces_existing: bool


def extract(collection: Collection, export_text: str, origin: str = "Moodle export") -> list[Path]:
    """Write the questions of a Moodle export as question sources; returns the written paths."""
    existing = _index_by_question_id(collection)
    planned: list[ExtractedSource] = []
    taken: set[Path] = set()
    for exported in read_export(export_text, origin):
        planned.append(_plan(collection, exported, existing, taken))
        taken.add(planned[-1].path)
    dirty = [p for p in planned if p.replaces_existing and _uncommitted(collection.root, p.path)]
    if dirty:
        names = ", ".join(collection.relative(p.path).as_posix() for p in dirty)
        raise UserError(f"Not overwriting question sources with uncommitted changes: {names}.")
    for source in planned:
        source.path.parent.mkdir(parents=True, exist_ok=True)
        source.path.write_text(source.content, encoding="utf-8")
    return [source.path for source in planned]


def _plan(
    collection: Collection,
    exported: ExportedQuestion,
    existing: dict[str, Path],
    taken: set[Path],
) -> ExtractedSource:
    element = exported.element
    qtype = element.get("type", "")
    handler = handler_for(qtype)
    if handler is None:
        raise UserError(f"Question type {qtype!r} is not supported yet.")
    name = text_of(element, "name")
    question_id = text_of(element, "idnumber")

    existing_path = existing.get(question_id) if question_id else None
    existing_document = (
        parse_source(existing_path.read_text(encoding="utf-8"), str(existing_path))
        if existing_path
        else None
    )
    document = question_document(collection, handler, element, existing_document)

    if existing_path is not None:
        return ExtractedSource(existing_path, format_source(document), replaces_existing=True)

    category = _without_root_category(exported.category, collection.root_category)
    folder = collection.root / folder_for_category(category)
    path = _free_path(folder, slug(name) or "question", taken)
    derived_id = question_id_from_path(collection.relative(path))
    if not question_id:
        # Moodle has no question ID yet: record the new one so the next import carries it.
        question_id = question_id_from_category(exported.category, name)
        document.front_matter = {"id": question_id, **document.front_matter}
    elif question_id != derived_id:
        document.front_matter = {"id": question_id, **document.front_matter}
    return ExtractedSource(path, format_source(document), replaces_existing=False)


def question_document(
    collection: Collection,
    handler: QuestionType,
    element: ET.Element,
    existing: SourceDocument | None = None,
) -> SourceDocument:
    """The question source for one exported question, keeping what only the existing source
    knows (notes, explicit name/ID/category/lang)."""
    qtype = handler.name

    def markdown(html: str, files: dict[str, bytes]) -> str:
        return to_markdown(html, pre_style=collection.pre_style)

    text = read_field(element.find("questiontext"), markdown)
    settings: dict[str, Any] = {
        "points": _number(text_of(element, "defaultgrade", "1")),
        "penalty": _number(text_of(element, "penalty", "0")),
        "tags": [text_of(tag, "text") for tag in element.findall("tags/tag")],
    }
    if handler.combined_feedback:
        settings["feedback"] = {
            key: read_field(element.find(tag), markdown)
            for key, tag in (
                ("correct", "correctfeedback"),
                ("partially", "partiallycorrectfeedback"),
                ("incorrect", "incorrectfeedback"),
            )
        }
        settings["show_num_correct"] = element.find("shownumcorrect") is not None
    result = handler.read(element, text, markdown, existing)
    settings.update(result.settings)

    front_matter: dict[str, Any] = {"type": qtype}
    if existing:
        front_matter.update(
            {k: existing.front_matter[k] for k in KEPT_FROM_EXISTING if k in existing.front_matter}
        )
    front_matter.update(_differences(settings, collection.defaults_for(qtype)))
    name = text_of(element, "name")
    keeps_name = existing is not None and "name" in existing.front_matter
    if keeps_name:
        front_matter["name"] = name
    return SourceDocument(
        front_matter=front_matter,
        title=existing.title if keeps_name and existing else name,
        text=result.text if result.text is not None else text,
        answers=result.answers,
        solution=read_field(element.find("generalfeedback"), markdown),
        notes=existing.notes if existing else "",
    )


def _differences(settings: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Settings that differ from the defaults, in front matter form."""
    differing: dict[str, Any] = {}
    for key, value in settings.items():
        default = defaults.get(key)
        if key == "tags":
            extra = [tag for tag in value if tag not in (default or [])]
            if extra:
                differing[key] = extra
        elif key == "feedback":
            changed = {k: v for k, v in value.items() if (default or {}).get(k, "") != v}
            if changed:
                differing[key] = changed
        elif not _same(value, default):
            differing[key] = value
    return differing


def _same(value: Any, default: Any) -> bool:
    if isinstance(value, bool) or isinstance(default, bool):
        return bool(value) == bool(default) and type(value) is type(default)
    if isinstance(value, int | float) and isinstance(default, int | float):
        return float(value) == float(default)
    return bool(value == default)


def _number(text: str) -> int | float:
    value = float(text)
    return int(value) if value.is_integer() else value


def _index_by_question_id(collection: Collection) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in collection.sources([collection.root]):
        index[load_question(collection, path).question_id] = path
    return index


def _without_root_category(category: str, root_category: str | None) -> str:
    if root_category and (category == root_category or category.startswith(root_category + "/")):
        return category[len(root_category) :].strip("/")
    return category


def _free_path(folder: Path, stem: str, taken: set[Path]) -> Path:
    candidate = folder / f"{stem}.md"
    number = 2
    while candidate in taken or candidate.exists():
        candidate = folder / f"{stem}-{number}.md"
        number += 1
    return candidate


def _uncommitted(root: Path, path: Path) -> bool:
    """Whether git reports changes (or an untracked file) at ``path``; outside git: ``False``."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", str(path)],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0 and bool(result.stdout.strip())
