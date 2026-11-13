"""Helpers for tests that work on question collections in temporary folders."""

import shutil
import subprocess
from pathlib import Path

from moodle_qc.cli import main

FIXTURES = Path(__file__).parent.parent / "fixtures"


def moodle_fixture(name: str) -> str:
    return (FIXTURES / "moodle" / name).read_text(encoding="utf-8")


def copy_collection(name: str, target: Path) -> Path:
    shutil.copytree(FIXTURES / "collections" / name, target)
    return target


def empty_collection(target: Path, config: str = "") -> Path:
    target.mkdir(parents=True, exist_ok=True)
    (target / "moodle-qc.yaml").write_text(config, encoding="utf-8")
    return target


def git_commit_all(folder: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=folder, check=True, capture_output=True)

    if not (folder / ".git").exists():
        git("init", "-q")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x")


def generate(paths: list[Path], output: Path, *extra: str) -> str:
    exit_code = main(["generate", *map(str, paths), "--output", str(output), *extra])
    assert exit_code == 0
    return output.read_text(encoding="utf-8")


def extract(export: str, collection: Path, tmp: Path) -> int:
    export_file = tmp / "export.xml"
    export_file.write_text(export, encoding="utf-8")
    return main(["extract", str(export_file), "--into", str(collection)])


def sources(collection: Path) -> dict[str, str]:
    """All question sources of a collection by relative path."""
    return {
        path.relative_to(collection).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(collection.rglob("*.md"))
        if ".git" not in path.parts
    }
