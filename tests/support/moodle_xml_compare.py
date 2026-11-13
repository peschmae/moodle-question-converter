"""Compare two Moodle XML documents by content, not by formatting.

Compared: every category (path and description) and every question with all its elements,
attributes and texts.

Ignored on purpose, because Moodle changes these on import/export without changing content:

- formatting: indentation, whitespace around text, CDATA vs XML escaping, XML comments, and
  line breaks (with indentation) between HTML tags - except inside ``<pre>``, where every
  character counts
- numbers written differently (``1`` vs ``1.0000000``, ``0.0`` vs ``0``); only plain decimal
  numbers are compared as numbers
- an empty ``<idnumber>`` vs a missing one
- the order of questions and categories; questions are matched by category and question ID
  (else question name), and in document order when several share both
- category paths written with or without a ``$course$/top/`` prefix, and the entries for parent
  categories that Moodle adds on export
- the ``format`` attribute of ``<responsetext>`` (``kprime``/``mtf`` judgement labels): the ETH
  plugins read only its text, and Moodle's re-export of our reference file changes it from
  ``html`` to ``moodle_auto_format``
"""

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass

PRESENT = "present"
"""Value of ``expected``/``actual`` for a question or element that only one document has."""

_CONTEXT_PREFIX = re.compile(r"^\$(course|cat|module|system)\$/")
_PRE_BLOCK = re.compile(r"<pre\b.*?</pre>", re.DOTALL | re.IGNORECASE)
# NUL can never occur in XML text, so the placeholder can't clash with real content.
_PRE_PLACEHOLDER = re.compile(r"<\x00(\d+)>")
_LINE_BREAK_BETWEEN_TAGS = re.compile(r">\s*\n\s*<")
_PLAIN_DECIMAL = re.compile(r"-?\d+(\.\d+)?")
_EMPTY_EQUALS_MISSING = frozenset({"idnumber"})
_IGNORED_ATTRIBUTES = frozenset({("responsetext", "format")})
_CONTEXT_CHARS = 20
_LONG_TEXT = 50


@dataclass(frozen=True)
class Difference:
    """One place where the actual document differs from the expected one."""

    location: str
    expected: str | None
    actual: str | None

    def __str__(self) -> str:
        expected, actual = self.expected, self.actual
        if (
            expected is not None
            and actual is not None
            and max(len(expected), len(actual)) > _LONG_TEXT
        ):
            at = _first_difference(expected, actual)
            return (
                f"{self.location}: at character {at}: "
                f"expected {_excerpt(expected, at)!r}, got {_excerpt(actual, at)!r}"
            )
        return f"{self.location}: expected {expected!r}, got {actual!r}"


@dataclass(frozen=True)
class _Question:
    category: str
    question_id: str
    name: str
    element: ET.Element

    @property
    def identity(self) -> tuple[str, str]:
        return (self.category, self.question_id or self.name)

    @property
    def location(self) -> str:
        qtype = self.element.get("type", "?")
        where = f"{self.category}/" if self.category else ""
        return f"question {where}{self.question_id or self.name} ({qtype})"


@dataclass(frozen=True)
class _Document:
    categories: dict[str, str]
    """Category path → description, including every parent category."""
    questions: dict[tuple[str, str], list[_Question]]
    """Question identity → questions with that identity, in document order."""


def compare_moodle_xml(
    expected: str, actual: str, *, ignore_question_ids: bool = False
) -> list[Difference]:
    """Return the content differences between two Moodle XML documents (empty if equal).

    ``ignore_question_ids`` compares hand-made fixtures without ``<idnumber>`` to generated
    import files, which always carry a question ID.
    """
    expected_document = _parse(expected, ignore_question_ids)
    actual_document = _parse(actual, ignore_question_ids)
    return _compare_categories(expected_document, actual_document) + _compare_questions(
        expected_document, actual_document
    )


def assert_moodle_xml_equal(
    expected: str, actual: str, *, ignore_question_ids: bool = False
) -> None:
    """Fail with all differences listed if the documents differ in content."""
    differences = compare_moodle_xml(expected, actual, ignore_question_ids=ignore_question_ids)
    if differences:
        listing = "\n".join(f"  - {d}" for d in differences)
        raise AssertionError(f"Moodle XML differs in {len(differences)} place(s):\n{listing}")


def _parse(document: str, ignore_question_ids: bool) -> _Document:
    categories: dict[str, str] = {}
    questions: dict[tuple[str, str], list[_Question]] = defaultdict(list)
    root = ET.fromstring(document)
    if ignore_question_ids:
        for element in root.findall("question"):
            for idnumber in element.findall("idnumber"):
                element.remove(idnumber)
    for question in _questions(root, categories):
        questions[question.identity].append(question)
    for path in list(categories):
        for parent in _parents(path):
            categories.setdefault(parent, "")
    return _Document(categories, dict(questions))


def _questions(root: ET.Element, categories: dict[str, str]) -> Iterator[_Question]:
    category = ""
    for element in root.findall("question"):
        if element.get("type") == "category":
            category = _category_path(element.findtext("category/text", default=""))
            if category:
                categories[category] = _text(element.find("info/text"))
            continue
        question_id = _text(element.find("idnumber"))
        name = _text(element.find("name/text"))
        yield _Question(category, question_id, name, element)


def _category_path(raw: str) -> str:
    path = _CONTEXT_PREFIX.sub("", raw.strip())
    if path == "top":
        return ""
    return path.removeprefix("top/")


def _parents(path: str) -> list[str]:
    parts = path.split("/")
    return ["/".join(parts[:end]) for end in range(1, len(parts))]


def _compare_categories(expected: _Document, actual: _Document) -> list[Difference]:
    differences: list[Difference] = []
    for path, expected_info in expected.categories.items():
        location = f"category {path}"
        if path not in actual.categories:
            differences.append(_only_in_expected(location))
        elif expected_info != actual.categories[path]:
            differences.append(
                Difference(f"{location} > info", expected_info, actual.categories[path])
            )
    differences.extend(
        _only_in_actual(f"category {path}")
        for path in actual.categories
        if path not in expected.categories
    )
    return differences


def _compare_questions(expected: _Document, actual: _Document) -> list[Difference]:
    differences: list[Difference] = []
    for identity, expected_questions in expected.questions.items():
        actual_questions = actual.questions.get(identity, [])
        for index, expected_question in enumerate(expected_questions):
            if index < len(actual_questions):
                differences.extend(
                    _compare_elements(
                        expected_question.element,
                        actual_questions[index].element,
                        expected_question.location,
                    )
                )
            else:
                differences.append(_only_in_expected(expected_question.location))
    for identity, actual_questions in actual.questions.items():
        surplus = actual_questions[len(expected.questions.get(identity, [])) :]
        differences.extend(_only_in_actual(question.location) for question in surplus)
    return differences


def _compare_elements(expected: ET.Element, actual: ET.Element, location: str) -> list[Difference]:
    differences: list[Difference] = []

    expected_text, actual_text = _text(expected), _text(actual)
    if not _values_equal(expected_text, actual_text):
        differences.append(Difference(location, expected_text, actual_text))

    for name in sorted(set(expected.attrib) | set(actual.attrib)):
        if (expected.tag, name) in _IGNORED_ATTRIBUTES:
            continue
        expected_value, actual_value = expected.get(name), actual.get(name)
        if not _values_equal(expected_value, actual_value):
            differences.append(Difference(f"{location} @{name}", expected_value, actual_value))

    for tag in _child_tags(expected, actual):
        expected_children = expected.findall(tag)
        actual_children = actual.findall(tag)
        if tag in _EMPTY_EQUALS_MISSING:
            expected_children = [c for c in expected_children if _text(c)]
            actual_children = [c for c in actual_children if _text(c)]
        count = max(len(expected_children), len(actual_children))
        for index in range(count):
            child_location = f"{location} > {tag}" + (f"[{index + 1}]" if count > 1 else "")
            if index >= len(actual_children):
                differences.append(_only_in_expected(child_location))
            elif index >= len(expected_children):
                differences.append(_only_in_actual(child_location))
            else:
                differences.extend(
                    _compare_elements(
                        expected_children[index], actual_children[index], child_location
                    )
                )
    return differences


def _text(element: ET.Element | None) -> str:
    """Text of an element without formatting noise; ``<pre>`` blocks are kept exactly."""
    if element is None or element.text is None:
        return ""
    pre_blocks: list[str] = []

    def set_aside(match: re.Match[str]) -> str:
        pre_blocks.append(match.group(0))
        return f"<\x00{len(pre_blocks) - 1}>"

    masked = _PRE_BLOCK.sub(set_aside, element.text.strip())
    collapsed = _LINE_BREAK_BETWEEN_TAGS.sub("><", masked)
    return _PRE_PLACEHOLDER.sub(lambda match: pre_blocks[int(match.group(1))], collapsed)


def _values_equal(expected: str | None, actual: str | None) -> bool:
    """Equal as written, or as plain decimal numbers; a missing value only equals itself."""
    if expected == actual:
        return True
    if expected is None or actual is None:
        return False
    if _PLAIN_DECIMAL.fullmatch(expected) and _PLAIN_DECIMAL.fullmatch(actual):
        return float(expected) == float(actual)
    return False


def _first_difference(expected: str, actual: str) -> int:
    for index, (a, b) in enumerate(zip(expected, actual, strict=False)):
        if a != b:
            return index
    return min(len(expected), len(actual))


def _excerpt(text: str, at: int) -> str:
    start, end = max(0, at - _CONTEXT_CHARS), at + _CONTEXT_CHARS
    return ("…" if start > 0 else "") + text[start:end] + ("…" if end < len(text) else "")


def _only_in_expected(location: str) -> Difference:
    return Difference(location, PRESENT, None)


def _only_in_actual(location: str) -> Difference:
    return Difference(location, None, PRESENT)


def _child_tags(*elements: ET.Element) -> list[str]:
    tags: list[str] = []
    for element in elements:
        for child in element:
            if child.tag not in tags:
                tags.append(child.tag)
    return tags


def select_questions(document: str, *qtypes: str) -> str:
    """Only the questions of ``qtypes`` (and the categories holding them) from a Moodle XML
    document."""
    root = ET.fromstring(document)
    pending_category: ET.Element | None = None
    for element in list(root.findall("question")):
        root.remove(element)
        if element.get("type") == "category":
            pending_category = element
        elif element.get("type") in qtypes:
            if pending_category is not None:
                root.append(pending_category)
                pending_category = None
            root.append(element)
    return ET.tostring(root, encoding="unicode")
