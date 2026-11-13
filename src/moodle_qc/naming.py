"""Category names and question IDs derived from folder and file names."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

_NOT_SLUG = re.compile(r"[^a-z0-9]+")


def category_name(folder: str) -> str:
    """Folder name → category name: ``_`` becomes a space, the first letter of each word is
    capitalised, nothing else changes (``SW09_alerting`` → ``SW09 Alerting``)."""
    words = folder.replace("_", " ").split(" ")
    return " ".join(word[:1].upper() + word[1:] for word in words)


def category_path(folder: PurePosixPath, root_category: str | None = None) -> str:
    """Folder path relative to the collection root → category path, below the root category."""
    names = [category_name(part) for part in folder.parts]
    if root_category:
        names.insert(0, root_category.strip("/"))
    return "/".join(names)


def folder_for_category(category: str) -> PurePosixPath:
    """Category path → folder path for a newly extracted question (spaces become ``_``)."""
    return PurePosixPath(*[part.replace(" ", "_") for part in category.split("/") if part])


def slug(text: str) -> str:
    """Lower-case ASCII words joined by ``-``; umlauts are transliterated."""
    text = text.lower()
    for umlaut, ascii_ in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(umlaut, ascii_)
    return _NOT_SLUG.sub("-", text).strip("-")


def question_id_from_path(relative_source: PurePosixPath) -> str:
    """Question ID of a question source, from its path relative to the collection root."""
    return slug("-".join(relative_source.with_suffix("").parts))


def question_id_from_category(category: str, question_name: str) -> str:
    """Question ID for an extracted question without one: category + question name."""
    return slug(f"{category}-{question_name}")
