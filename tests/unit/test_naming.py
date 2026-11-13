from pathlib import PurePosixPath

import pytest

from moodle_qc.naming import (
    category_name,
    category_path,
    folder_for_category,
    question_id_from_category,
    question_id_from_path,
)


def test_question_id_from_source_path() -> None:
    assert (
        question_id_from_path(PurePosixPath("SW09_alerting/Latenz SLI.md"))
        == "sw09-alerting-latenz-sli"
    )


def test_question_id_transliterates_umlauts() -> None:
    assert question_id_from_path(PurePosixPath("übung/größe.md")) == "uebung-groesse"


def test_question_id_from_category_and_question_name() -> None:
    assert (
        question_id_from_category("import-test/SW09", "Latenz-SLI und fehlendes Target")
        == "import-test-sw09-latenz-sli-und-fehlendes-target"
    )


def test_folder_for_a_new_category_replaces_spaces() -> None:
    assert folder_for_category("SW09 Alerting/Burn Rate") == PurePosixPath(
        "SW09_Alerting/Burn_Rate"
    )


@pytest.mark.parametrize(
    ("folder", "category"),
    [
        ("SW09_alerting", "SW09 Alerting"),
        ("otel_collector", "Otel Collector"),
        ("slo-und-sli", "Slo-und-sli"),
        ("Alerting Basics", "Alerting Basics"),
        ("sw09", "Sw09"),
        ("OTel_collector", "OTel Collector"),
    ],
)
def test_category_name_from_folder_name(folder: str, category: str) -> None:
    assert category_name(folder) == category


def test_nested_folders_become_a_category_path_below_the_root_category() -> None:
    assert (
        category_path(PurePosixPath("SW09_alerting/burn_rate"), "26hs")
        == "26hs/SW09 Alerting/Burn Rate"
    )


def test_questions_at_the_collection_root_have_only_the_root_category() -> None:
    assert category_path(PurePosixPath("."), "26hs") == "26hs"
    assert category_path(PurePosixPath("."), None) == ""
