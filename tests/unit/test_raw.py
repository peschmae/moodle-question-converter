import xml.etree.ElementTree as ET

from moodle_qc.qtypes.raw import RawQuestion
from moodle_qc.xmlnode import serialize
from tests.support.questions import question

XML = '```xml\n<question type="essay"><name><text>Essay</text></name><idnumber /></question>\n```'


def test_raw_question_is_written_back_with_its_question_id() -> None:
    node = RawQuestion().node(question("raw", text=XML))

    element = ET.fromstring(serialize(node))
    assert element.get("type") == "essay"
    assert element.findtext("idnumber") == "q"
    assert element.findtext("name/text") == "Essay"


def test_inner_question_type() -> None:
    assert RawQuestion().inner_type(question("raw", text=XML)) == "essay"


def test_malformed_raw_question_sources_are_reported() -> None:
    assert RawQuestion().validate(question("raw", text="kein XML")) == [
        "a raw question source holds exactly one ```xml block with a <question>"
    ]
    assert RawQuestion().validate(question("raw", text="```xml\n<quiz/>\n```")) == [
        'the ```xml block must hold one <question type="…"> element'
    ]


def test_reading_stores_the_xml_without_question_id() -> None:
    element = ET.fromstring('<question type="essay"><idnumber>x-1</idnumber></question>')

    result = RawQuestion().read(element, "", lambda html, files: html)

    assert result.text == '```xml\n<question type="essay"><idnumber /></question>\n```'
