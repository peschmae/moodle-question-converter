from pathlib import Path

from moodle_qc.cli import main
from tests.support.collections import copy_collection


def test_preview_shows_questions_answers_gaps_and_solution(tmp_path: Path) -> None:
    reference = copy_collection("reference", tmp_path / "reference")
    gaps = copy_collection("ddwtos", tmp_path / "ddwtos")
    output = tmp_path / "preview.html"

    assert main(["preview", str(reference), "--output", str(output)]) == 0
    page = output.read_text(encoding="utf-8")
    assert "SW07 – Prometheus Datenmodell" in page
    assert "SW09 – SLO-Begriffe" in page
    assert '<li class="correct"><span class="mark">✓ 50%</span>' in page
    assert "richtig" in page

    assert main(["preview", str(gaps), "--output", str(output)]) == 0
    page = output.read_text(encoding="utf-8")
    assert '<span class="gap">record</span>' in page
    assert "keep_firing_for" in page
    assert '<div class="solution-title">Solution</div>' in page


def test_preview_lists_problems_and_exits_non_zero(tmp_path: Path) -> None:
    collection = copy_collection("reference", tmp_path / "q")
    (collection / "bad.md").write_text("# Ohne Typ\n", encoding="utf-8")
    output = tmp_path / "preview.html"

    assert main(["preview", str(collection), "--output", str(output)]) == 1
    page = output.read_text(encoding="utf-8")
    assert "bad.md: front matter has no question type" in page
    assert "SW09 – SLO-Begriffe" in page
