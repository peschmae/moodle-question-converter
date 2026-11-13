import shutil
from pathlib import Path

import pytest

from moodle_qc.cli import main
from tests.support.moodle_xml_compare import assert_moodle_xml_equal, select_questions

FIXTURES = Path(__file__).parent.parent / "fixtures"
REFERENCE_XML = (FIXTURES / "moodle" / "moodle-xml-reference.xml").read_text(encoding="utf-8")


@pytest.fixture
def reference_collection(tmp_path: Path) -> Path:
    collection = tmp_path / "questions"
    shutil.copytree(FIXTURES / "collections" / "reference", collection)
    return collection


def run_generate(paths: list[Path], output: Path, *extra: str) -> int:
    return main(["generate", *map(str, paths), "--output", str(output), *extra])


def test_generates_the_sc_question_of_the_reference_file(
    reference_collection: Path, tmp_path: Path
) -> None:
    output = tmp_path / "import.xml"

    exit_code = run_generate([reference_collection / "SW09"], output)

    assert exit_code == 0
    assert_moodle_xml_equal(
        select_questions(REFERENCE_XML, "sc"),
        output.read_text(encoding="utf-8"),
        ignore_question_ids=True,
    )


def test_text_is_written_as_cdata_and_category_without_course_prefix(
    reference_collection: Path, tmp_path: Path
) -> None:
    output = tmp_path / "import.xml"

    run_generate([reference_collection / "SW09" / "slo-begriffe.md"], output)

    generated = output.read_text(encoding="utf-8")
    assert "<text><![CDATA[<p>Was beschreibt ein Error Budget?</p>]]></text>" in generated
    assert "<text>import-test/SW09</text>" in generated
    assert "$course$" not in generated


def test_question_id_is_derived_from_the_source_path(
    reference_collection: Path, tmp_path: Path
) -> None:
    output = tmp_path / "import.xml"

    run_generate([reference_collection], output)

    assert "<idnumber>sw09-slo-begriffe</idnumber>" in output.read_text(encoding="utf-8")


def test_finds_the_collection_root_from_a_subfolder(
    reference_collection: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(reference_collection / "SW09")

    exit_code = main(["generate", ".", "--output", str(tmp_path / "import.xml")])

    assert exit_code == 0
    assert "<text>import-test/SW09</text>" in (tmp_path / "import.xml").read_text(encoding="utf-8")


def test_without_collection_config_reports_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "q.md").write_text("---\ntype: sc\n---\n", encoding="utf-8")

    exit_code = run_generate([tmp_path / "q.md"], tmp_path / "import.xml")

    assert exit_code == 1
    assert "No moodle-qc.yaml found" in capsys.readouterr().err
