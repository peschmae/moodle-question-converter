import pytest

from moodle_qc.errors import UserError
from moodle_qc.moodle_xml import normalize_category, read_export


@pytest.mark.parametrize(
    ("raw", "category"),
    [
        ("$course$/top/import-test/SW07", "import-test/SW07"),
        ("$course$/top", ""),
        ("$module$/top/Sammlung", "Sammlung"),
        ("import-test/SW07", "import-test/SW07"),
    ],
)
def test_category_paths_lose_moodle_context_prefixes(raw: str, category: str) -> None:
    assert normalize_category(raw) == category


def test_questions_belong_to_the_preceding_category_entry() -> None:
    export = (
        "<quiz>"
        '<question type="sc"><name><text>A</text></name></question>'
        '<question type="category"><category><text>$course$/top/sw09</text></category></question>'
        '<question type="sc"><name><text>B</text></name></question>'
        "</quiz>"
    )

    assert [(q.category, q.element.findtext("name/text")) for q in read_export(export)] == [
        ("", "A"),
        ("sw09", "B"),
    ]


def test_invalid_files_are_reported() -> None:
    with pytest.raises(UserError, match=r"export\.xml: not valid XML"):
        read_export("<quiz>", "export.xml")
    with pytest.raises(UserError, match="not a Moodle XML file"):
        read_export("<html/>")
