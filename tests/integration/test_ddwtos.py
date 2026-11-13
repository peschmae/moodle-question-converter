from pathlib import Path

from tests.support.collections import (
    copy_collection,
    empty_collection,
    extract,
    generate,
    git_commit_all,
    moodle_fixture,
    sources,
)
from tests.support.moodle_xml_compare import assert_moodle_xml_equal


def test_gap_questions_generate_the_hand_written_import_file(tmp_path: Path) -> None:
    collection = copy_collection("ddwtos", tmp_path / "questions")

    generated = generate([collection], tmp_path / "import.xml")

    assert_moodle_xml_equal(
        moodle_fixture("sample-ddwtos.xml"), generated, ignore_question_ids=True
    )


def test_generate_then_extract_keeps_gap_group_names(tmp_path: Path) -> None:
    collection = copy_collection("ddwtos", tmp_path / "questions")
    git_commit_all(collection)
    original = sources(collection)

    extract(generate([collection], tmp_path / "import.xml"), collection, tmp_path)

    assert sources(collection) == original


def test_moodle_export_with_manual_edits_extracts_to_inline_gaps(tmp_path: Path) -> None:
    collection = empty_collection(tmp_path / "questions")

    assert extract(moodle_fixture("sample-ddwtos-export.xml"), collection, tmp_path) == 0

    [(path, content)] = sources(collection).items()
    assert path == "latenz-sli-und-fehlendes-target.md"
    assert content.startswith(
        "---\n"
        "type: ddwtos\n"
        "id: latenz-sli-und-fehlendes-target\n"
        "points: 4\n"
        "penalty: 0\n"
        "distractors:\n"
        "  group1: [sum, total]\n"
        "  group2: ['5', '5000']\n"
        "  group3: [absent_over_time, count]\n"
        "  group4: [== 0, '> 1']\n"
        "---\n\n"
        "# Latenz-SLI und fehlendes Target\n\n"
    )
    assert "```\n- record: service:chatbot_reply_slow:ratio_rate5m\n" in content
    assert 'seconds_[[bucket|group1]]{le="[[5.0|group2]]"}[5m]' in content
    assert "expr: [[absent|group3]](up{" in content


def test_moodle_export_round_trips_through_extract_and_generate(tmp_path: Path) -> None:
    export = moodle_fixture("sample-ddwtos-export.xml")
    collection = empty_collection(tmp_path / "questions")
    extract(export, collection, tmp_path)

    generated = generate([collection], tmp_path / "import.xml")

    assert_moodle_xml_equal(export, generated, ignore_question_ids=True)
