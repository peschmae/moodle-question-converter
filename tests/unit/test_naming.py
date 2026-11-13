from pathlib import PurePosixPath

from moodle_qc.naming import question_id_from_category, question_id_from_path


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
