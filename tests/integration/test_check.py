from pathlib import Path

import pytest

from moodle_qc.cli import main
from tests.support.collections import copy_collection, empty_collection

SC = "---\ntype: sc\n{extra}---\n# Q\n\nText\n\n## Answers\n{answers}\n"
TWO_ANSWERS = "- [ ] a\n- [x] b"


def write(collection: Path, name: str, extra: str = "", answers: str = TWO_ANSWERS) -> None:
    path = collection / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SC.format(extra=extra, answers=answers), encoding="utf-8")


def test_valid_collection_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    collection = copy_collection("reference", tmp_path / "questions")

    assert main(["check", str(collection)]) == 0
    assert "OK:" in capsys.readouterr().out


def test_problems_name_the_question_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    collection = empty_collection(tmp_path / "q", "allowed_types: [sc, multichoice]\n")
    write(collection, "a/two-correct.md", answers="- [x] a\n- [x] b")
    write(collection, "a/unknown-key.md", extra="colour: red\n")
    (collection / "b").mkdir()
    (collection / "b" / "kprime.md").write_text(
        SC.format(extra="", answers=TWO_ANSWERS).replace("type: sc", "type: kprime"),
        encoding="utf-8",
    )
    (collection / "b" / "no-answers.md").write_text(
        "---\ntype: sc\n---\n# Q\n\nText\n", encoding="utf-8"
    )
    (collection / "b" / "no-type.md").write_text("# Q\n", encoding="utf-8")

    exit_code = main(["check", str(collection)])

    assert exit_code == 1
    assert capsys.readouterr().err.splitlines() == [
        "a/two-correct.md: needs exactly one correct answer ([x]), has 2",
        "a/unknown-key.md: unknown front matter key(s): colour",
        "b/kprime.md: question type 'kprime' is not allowed by the collection config (allowed: multichoice, sc)",
        "b/no-answers.md: has no '## Answers' section",
        "b/no-type.md: front matter has no question type (type: …).",
        "5 problem(s) found.",
    ]


def test_duplicate_question_ids_are_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    collection = empty_collection(tmp_path / "q")
    write(collection, "a.md", extra="id: same\n")
    write(collection, "b.md", extra="id: same\n")

    assert main(["check", str(collection)]) == 1
    assert capsys.readouterr().err.splitlines()[:2] == [
        "a.md: question ID 'same' is also used by b.md",
        "b.md: question ID 'same' is also used by a.md",
    ]


def test_generate_writes_nothing_when_validation_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    collection = empty_collection(tmp_path / "q")
    write(collection, "bad.md", answers="- [ ] a\n- [ ] b")
    output = tmp_path / "import.xml"

    exit_code = main(["generate", str(collection), "--output", str(output)])

    assert exit_code == 1
    assert not output.exists()
    assert "bad.md: needs exactly one correct answer ([x]), has 0" in capsys.readouterr().err
