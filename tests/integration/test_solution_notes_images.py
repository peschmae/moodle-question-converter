import base64
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from moodle_qc.cli import main
from tests.support.collections import empty_collection, extract, generate, git_commit_all, sources

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
OTHER_PNG = PNG + b"\0"

QUESTION = """---
type: sc
---

# Dashboard

Welches Panel zeigt ![Panel](dashboard.png) den Fehler?

## Answers
- [x] Das obere ![Logo](../shared/logo.png)
- [ ] Das untere

## Solution

Siehe ![Panel](dashboard.png) oben links.

## Notes

Bild aus Grafana, Woche 9.
"""


@pytest.fixture
def collection(tmp_path: Path) -> Path:
    root = empty_collection(tmp_path / "questions")
    (root / "sw09").mkdir()
    (root / "shared").mkdir()
    (root / "sw09" / "dashboard.md").write_text(QUESTION, encoding="utf-8")
    (root / "sw09" / "dashboard.png").write_bytes(PNG)
    (root / "shared" / "logo.png").write_bytes(OTHER_PNG)
    return root


def test_images_are_embedded_and_solution_goes_to_general_feedback(
    collection: Path, tmp_path: Path
) -> None:
    question = ET.fromstring(generate([collection], tmp_path / "import.xml")).findall("question")[1]

    text = question.find("questiontext")
    assert text is not None
    assert '<img src="@@PLUGINFILE@@/dashboard.png" alt="Panel">' in (text.findtext("text") or "")
    [file] = text.findall("file")
    assert (file.get("name"), file.get("path"), file.get("encoding")) == (
        "dashboard.png",
        "/",
        "base64",
    )
    assert base64.b64decode(file.text or "") == PNG
    assert "Siehe" in (question.findtext("generalfeedback/text") or "")
    assert question.find("generalfeedback/file") is not None
    assert question.find("row/optiontext/file") is not None


def test_notes_are_never_generated(collection: Path, tmp_path: Path) -> None:
    assert "Grafana, Woche 9" not in generate([collection], tmp_path / "import.xml")


def test_round_trip_keeps_image_paths_notes_and_writes_no_new_files(
    collection: Path, tmp_path: Path
) -> None:
    git_commit_all(collection)
    files_before = sorted(
        p.relative_to(collection) for p in collection.rglob("*") if ".git" not in p.parts
    )
    original = sources(collection)

    extract(generate([collection], tmp_path / "import.xml"), collection, tmp_path)

    assert sources(collection) == original
    assert (
        sorted(p.relative_to(collection) for p in collection.rglob("*") if ".git" not in p.parts)
        == files_before
    )


def test_extract_writes_embedded_images_next_to_a_new_question_source(
    collection: Path, tmp_path: Path
) -> None:
    export = generate([collection], tmp_path / "import.xml")
    target = empty_collection(tmp_path / "other")

    extract(export, target, tmp_path)

    assert (target / "Sw09" / "dashboard.png").read_bytes() == PNG
    assert (target / "Sw09" / "logo.png").read_bytes() == OTHER_PNG
    content = (target / "Sw09" / "dashboard.md").read_text(encoding="utf-8")
    assert "![Panel](dashboard.png)" in content
    assert "- [x] Das obere ![Logo](logo.png)" in content


def test_check_reports_missing_images(collection: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (collection / "sw09" / "dashboard.png").unlink()

    assert main(["check", str(collection)]) == 1
    assert (
        capsys.readouterr().err.splitlines()[0]
        == "sw09/dashboard.md: image dashboard.png not found"
    )
