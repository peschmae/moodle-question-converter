from pathlib import Path

import pytest

from moodle_qc.cli import main
from tests.support.collections import (
    empty_collection,
    extract,
    generate,
    git_commit_all,
    moodle_fixture,
    sources,
)
from tests.support.moodle_xml_compare import assert_moodle_xml_equal


def test_unsupported_question_type_becomes_a_raw_question_source(tmp_path: Path) -> None:
    collection = empty_collection(tmp_path / "questions")

    assert extract(moodle_fixture("sample-ddimageortext.xml"), collection, tmp_path) == 0

    [(path, content)] = sources(collection).items()
    assert path == "zuordnung-metrik-typen.md"
    assert content.startswith(
        "---\ntype: raw\nid: zuordnung-metrik-typen\n---\n\n# Zuordnung Metrik-Typen\n\n```xml\n"
        '<question type="ddimageortext">'
    )


def test_raw_question_source_generates_the_original_question(tmp_path: Path) -> None:
    export = moodle_fixture("sample-ddimageortext.xml")
    collection = empty_collection(tmp_path / "questions")
    extract(export, collection, tmp_path)

    generated = generate([collection], tmp_path / "import.xml")

    assert_moodle_xml_equal(export, generated, ignore_question_ids=True)
    assert "<idnumber>zuordnung-metrik-typen</idnumber>" in generated


def test_raw_question_source_is_overwritten_in_place(tmp_path: Path) -> None:
    collection = empty_collection(tmp_path / "questions")
    extract(moodle_fixture("sample-ddimageortext.xml"), collection, tmp_path)
    git_commit_all(collection)
    original = sources(collection)

    extract(generate([collection], tmp_path / "import.xml"), collection, tmp_path)

    assert sources(collection) == original


def test_check_accepts_raw_sources_and_applies_general_rules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    collection = empty_collection(tmp_path / "questions", "allowed_types: [sc]\n")
    extract(moodle_fixture("sample-ddimageortext.xml"), collection, tmp_path)
    (collection / "broken.md").write_text(
        "---\ntype: raw\n---\n# B\n\nKein XML\n", encoding="utf-8"
    )

    assert main(["check", str(collection)]) == 1
    assert capsys.readouterr().err.splitlines()[:2] == [
        "broken.md: a raw question source holds exactly one ```xml block with a <question>",
        "zuordnung-metrik-typen.md: question type 'ddimageortext' is not allowed by the collection "
        "config (allowed: sc)",
    ]
