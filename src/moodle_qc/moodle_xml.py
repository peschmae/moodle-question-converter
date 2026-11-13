"""Reading Moodle XML exports."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from moodle_qc.errors import UserError

_CONTEXT_PREFIX = re.compile(r"^\$(course|cat|module|system)\$/")


@dataclass
class ExportedQuestion:
    category: str
    """Category path without Moodle's ``$course$/top/`` prefix."""
    element: ET.Element


def read_export(text: str, origin: str = "Moodle export") -> list[ExportedQuestion]:
    """The questions of a Moodle XML export, each with the category it belongs to."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise UserError(f"{origin}: not valid XML: {error}") from None
    if root.tag != "quiz":
        raise UserError(f"{origin}: not a Moodle XML file (expected <quiz>).")
    questions: list[ExportedQuestion] = []
    category = ""
    for element in root.findall("question"):
        if element.get("type") == "category":
            category = normalize_category(element.findtext("category/text", default=""))
        else:
            questions.append(ExportedQuestion(category, element))
    return questions


def normalize_category(raw: str) -> str:
    """``$course$/top/import-test/SW07`` → ``import-test/SW07``."""
    path = _CONTEXT_PREFIX.sub("", raw.strip()).strip("/")
    if path == "top":
        return ""
    return path.removeprefix("top/")
