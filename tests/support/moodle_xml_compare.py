"""Compare two Moodle XML documents by content, not by formatting.

Ignored on purpose (Moodle changes these on import/export without changing the question):

- formatting: indentation, whitespace around text, line breaks between HTML tags,
  CDATA vs XML escaping, XML comments
- numbers written differently (``1`` vs ``1.0000000``, ``0.0`` vs ``0``)
- an empty ``<idnumber>`` vs a missing one
- the order of questions; questions are matched by category and question ID (or question name)
- category paths written with or without the ``$course$/top/`` prefix, and the extra entries
  for parent categories that Moodle writes on export
- the ``format`` attribute of ``<responsetext>`` (``kprime``/``mtf`` judgement labels), which
  the ETH plugins ignore on import
"""

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass

_CONTEXT_PREFIX = re.compile(r"^\$(course|cat|module|system)\$/")
_WHITESPACE_BETWEEN_TAGS = re.compile(r">\s*\n\s*<")
_EMPTY_EQUALS_MISSING = frozenset({"idnumber"})
_IGNORED_ATTRIBUTES = frozenset({("responsetext", "format")})


@dataclass(frozen=True)
class Difference:
    """One place where the actual document differs from the expected one."""

    location: str
    expected: str | None
    actual: str | None

    def __str__(self) -> str:
        return f"{self.location}: expected {self.expected!r}, got {self.actual!r}"


@dataclass(frozen=True)
class _Question:
    category: str
    key: str
    element: ET.Element

    @property
    def label(self) -> str:
        qtype = self.element.get("type", "?")
        where = f"{self.category}/" if self.category else ""
        return f"question {where}{self.key} ({qtype})"


def compare_moodle_xml(expected: str, actual: str) -> list[Difference]:
    """Return the content differences between two Moodle XML documents (empty if equal)."""
    expected_questions = {(q.category, q.key): q for q in _questions(expected)}
    actual_questions = {(q.category, q.key): q for q in _questions(actual)}

    differences: list[Difference] = []
    for ident, question in expected_questions.items():
        other = actual_questions.get(ident)
        if other is None:
            differences.append(Difference(question.label, "present", None))
        else:
            differences.extend(_compare_elements(question.element, other.element, question.label))
    for ident, question in actual_questions.items():
        if ident not in expected_questions:
            differences.append(Difference(question.label, None, "present"))
    return differences


def assert_moodle_xml_equal(expected: str, actual: str) -> None:
    """Fail with all differences listed if the documents differ in content."""
    differences = compare_moodle_xml(expected, actual)
    if differences:
        listing = "\n".join(f"  - {d}" for d in differences)
        raise AssertionError(f"Moodle XML differs in {len(differences)} place(s):\n{listing}")


def _questions(document: str) -> Iterator[_Question]:
    root = ET.fromstring(document)
    category = ""
    for element in root.findall("question"):
        if element.get("type") == "category":
            category = _category_path(element.findtext("category/text", default=""))
            continue
        idnumber = _text(element.find("idnumber"))
        key = idnumber or _text(element.find("name/text"))
        yield _Question(category, key, element)


def _category_path(raw: str) -> str:
    path = _CONTEXT_PREFIX.sub("", raw.strip())
    if path == "top":
        return ""
    return path.removeprefix("top/")


def _text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return _WHITESPACE_BETWEEN_TAGS.sub("><", element.text.strip())


def _values_equal(expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    try:
        return float(expected) == float(actual)
    except ValueError:
        return False


def _compare_elements(expected: ET.Element, actual: ET.Element, location: str) -> list[Difference]:
    differences: list[Difference] = []

    expected_text, actual_text = _text(expected), _text(actual)
    if not _values_equal(expected_text, actual_text):
        differences.append(Difference(location, expected_text, actual_text))

    for name in sorted(set(expected.attrib) | set(actual.attrib)):
        if (expected.tag, name) in _IGNORED_ATTRIBUTES:
            continue
        expected_value, actual_value = expected.get(name), actual.get(name)
        if expected_value is None or actual_value is None:
            if expected_value != actual_value:
                differences.append(Difference(f"{location} @{name}", expected_value, actual_value))
        elif not _values_equal(expected_value, actual_value):
            differences.append(Difference(f"{location} @{name}", expected_value, actual_value))

    for tag in _child_tags(expected, actual):
        expected_children = expected.findall(tag)
        actual_children = actual.findall(tag)
        if tag in _EMPTY_EQUALS_MISSING:
            expected_children = [c for c in expected_children if _text(c)]
            actual_children = [c for c in actual_children if _text(c)]
        for index in range(max(len(expected_children), len(actual_children))):
            child_location = f"{location} > {tag}"
            if max(len(expected_children), len(actual_children)) > 1:
                child_location += f"[{index + 1}]"
            if index >= len(actual_children):
                differences.append(Difference(child_location, "present", None))
            elif index >= len(expected_children):
                differences.append(Difference(child_location, None, "present"))
            else:
                differences.extend(
                    _compare_elements(
                        expected_children[index], actual_children[index], child_location
                    )
                )
    return differences


def _child_tags(*elements: ET.Element) -> list[str]:
    tags: list[str] = []
    for element in elements:
        for child in element:
            if child.tag not in tags:
                tags.append(child.tag)
    return tags
