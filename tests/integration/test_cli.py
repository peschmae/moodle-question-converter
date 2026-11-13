import re

import pytest

from moodle_qc.cli import main


def test_version_prints_tool_name_and_version(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--version"])

    assert exit_code == 0
    assert re.fullmatch(r"moodle-qc \d+\.\d+\.\d+", capsys.readouterr().out.strip())


def test_help_describes_the_question_converter(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--help"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: moodle-qc")
    assert "Moodle XML" in out
