from pathlib import Path

import pytest

from tests.support.collections import (
    copy_collection,
    empty_collection,
    extract,
    generate,
    git_commit_all,
    moodle_fixture,
    sources,
)
from tests.support.moodle_xml_compare import assert_moodle_xml_equal, select_questions

REFERENCE_CONFIG = (
    Path(__file__).parent.parent / "fixtures" / "collections" / "reference" / "moodle-qc.yaml"
).read_text(encoding="utf-8")


def test_extracts_an_sc_question_from_a_moodle_export(tmp_path: Path) -> None:
    collection = empty_collection(tmp_path / "questions", REFERENCE_CONFIG)

    exit_code = extract(
        select_questions(moodle_fixture("moodle-xml-reference.reexport.xml"), "sc"),
        collection,
        tmp_path,
    )

    assert exit_code == 0
    assert sources(collection) == {
        "SW09/sw09-slo-begriffe.md": (
            "---\n"
            "type: sc\n"
            "id: import-test-sw09-sw09-slo-begriffe\n"
            "---\n\n"
            "# SW09 – SLO-Begriffe\n\n"
            "Was beschreibt ein Error Budget?\n\n"
            "## Answers\n"
            "- [ ] Das Budget für Monitoring-Infrastruktur.\n"
            "- [x] Die erlaubte Unzuverlässigkeit gemäss SLO (1 − SLO).\n"
            "- [ ] Die maximale Anzahl Alerts pro Woche.\n"
        )
    }


def test_generate_then_extract_returns_the_original_question_sources(tmp_path: Path) -> None:
    collection = copy_collection("reference", tmp_path / "questions")
    git_commit_all(collection)
    original = sources(collection)
    generated = generate([collection], tmp_path / "import.xml")

    exit_code = extract(generated, collection, tmp_path)

    assert exit_code == 0
    assert sources(collection) == original


def test_extract_then_generate_gives_the_same_moodle_xml(tmp_path: Path) -> None:
    export = select_questions(moodle_fixture("moodle-xml-reference.reexport.xml"), "sc")
    collection = empty_collection(tmp_path / "questions", REFERENCE_CONFIG)
    extract(export, collection, tmp_path)

    generated = generate([collection], tmp_path / "import.xml")

    assert_moodle_xml_equal(export, generated, ignore_question_ids=True)


def test_existing_question_id_is_overwritten_where_it_is(tmp_path: Path) -> None:
    collection = copy_collection("reference", tmp_path / "questions")
    moved = collection / "anywhere" / "error-budget.md"
    moved.parent.mkdir()
    (collection / "SW09" / "slo-begriffe.md").rename(moved)
    moved.write_text(
        moved.read_text(encoding="utf-8").replace("type: sc", "type: sc\nid: eb"), encoding="utf-8"
    )
    git_commit_all(collection)
    export = generate([moved], tmp_path / "import.xml").replace(
        "Was beschreibt ein Error Budget?", "Was ist ein Error Budget?"
    )

    extract(export, collection, tmp_path)

    assert list(sources(collection)) == ["anywhere/error-budget.md"]
    assert "Was ist ein Error Budget?" in moved.read_text(encoding="utf-8")


def test_refuses_to_overwrite_uncommitted_changes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    collection = copy_collection("reference", tmp_path / "questions")
    git_commit_all(collection)
    generated = generate([collection], tmp_path / "import.xml")
    source = collection / "SW09" / "slo-begriffe.md"
    source.write_text(
        source.read_text(encoding="utf-8").replace("Error Budget", "Fehlerbudget"), encoding="utf-8"
    )
    edited = source.read_text(encoding="utf-8")

    exit_code = extract(generated, collection, tmp_path)

    assert exit_code == 1
    assert "uncommitted changes: SW09/slo-begriffe.md" in capsys.readouterr().err
    assert source.read_text(encoding="utf-8") == edited


def test_unreadable_question_source_stops_extract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    collection = copy_collection("reference", tmp_path / "questions")
    (collection / "broken.md").write_text(
        "---\ntype: sc\n---\n# Q\n\n## Answers\n* x\n", encoding="utf-8"
    )

    exit_code = extract(
        select_questions(moodle_fixture("moodle-xml-reference.reexport.xml"), "sc"),
        collection,
        tmp_path,
    )

    assert exit_code == 1
    assert "broken.md: can't read answer line" in capsys.readouterr().err
    assert not (collection / "SW09" / "sw09-slo-begriffe.md").exists()
