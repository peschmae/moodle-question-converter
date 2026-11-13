"""Raw question sources: questions of types without a source format, kept as Moodle XML.

The question text of a raw question source is one fenced block holding the original
``<question>`` element::

    ---
    type: raw
    ---
    # Zuordnung Metrik-Typen

    ```xml
    <question type="ddimageortext">…</question>
    ```

Generate writes that element back unchanged, except that ``<idnumber>`` carries the question ID;
extract stores it with an empty ``<idnumber>``.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from moodle_qc.qtypes.base import BaseQuestionType, ReadResult
from moodle_qc.question import Question, Render, ToMarkdown
from moodle_qc.source import SourceDocument
from moodle_qc.xmlnode import Node

_XML_BLOCK = re.compile(r"\A```xml\n(.*)\n```\Z", re.DOTALL)


def question_element(question: Question) -> ET.Element:
    """The ``<question>`` element of a raw question source; ``ValueError`` if malformed."""
    match = _XML_BLOCK.match(question.document.text.strip())
    if not match:
        raise ValueError("a raw question source holds exactly one ```xml block with a <question>")
    try:
        element = ET.fromstring(match.group(1))
    except ET.ParseError as error:
        raise ValueError(f"the ```xml block is not valid XML: {error}") from None
    if element.tag != "question" or not element.get("type"):
        raise ValueError('the ```xml block must hold one <question type="…"> element')
    return element


def xml_block(element: ET.Element) -> str:
    return "```xml\n" + ET.tostring(element, encoding="unicode").strip() + "\n```"


class RawQuestion(BaseQuestionType):
    name = "raw"
    front_matter_keys: frozenset[str] = frozenset()
    has_answers = False
    combined_feedback = False

    def inner_type(self, question: Question) -> str | None:
        try:
            return question_element(question).get("type")
        except ValueError:
            return None

    def validate(self, question: Question) -> list[str]:
        try:
            question_element(question)
        except ValueError as error:
            return [str(error)]
        return []

    def node(self, question: Question) -> Node:
        """The ``<question>`` element as written to the import file."""
        element = question_element(question)
        idnumber = element.find("idnumber")
        if idnumber is None:
            idnumber = ET.SubElement(element, "idnumber")
        idnumber.text = question.question_id
        return Node("question", raw=ET.tostring(element, encoding="unicode"))

    def write(self, question: Question, node: Node, render: Render) -> None:
        raise NotImplementedError("raw questions are written whole, see RawQuestion.node")

    def read(
        self,
        element: ET.Element,
        text: str,
        to_markdown: ToMarkdown,
        existing: SourceDocument | None = None,
    ) -> ReadResult:
        # The question ID lives in the question source (path or front matter), not in the XML.
        for idnumber in element.findall("idnumber"):
            idnumber.text = None
        return ReadResult(text=xml_block(element))
