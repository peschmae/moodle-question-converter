"""The commands: generate, extract, check, preview."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from moodle_qc.collection import Collection
from moodle_qc.convert import import_file
from moodle_qc.extract import extract as extract_sources
from moodle_qc.preview import preview_page
from moodle_qc.validate import Problem, validate


def open_collection(paths: Sequence[Path], root_category: str | None = None) -> Collection:
    collection = Collection.find(paths[0])
    collection.root_category_override = root_category
    return collection


def generate(paths: Sequence[Path], output: Path, root_category: str | None = None) -> int:
    """Write one import file for the selected question sources; nothing if any is invalid."""
    collection = open_collection(paths, root_category)
    result = validate(collection, paths)
    if result.problems:
        _report(result.problems)
        print("No import file written.", file=sys.stderr)
        return 1
    output.write_text(import_file(collection, result.questions), encoding="utf-8")
    print(f"Wrote {len(result.questions)} question(s) to {output}")
    return 0


def check(paths: Sequence[Path]) -> int:
    """Validate the selected question sources without writing anything."""
    collection = open_collection(paths)
    result = validate(collection, paths)
    if result.problems:
        _report(result.problems)
        return 1
    print(f"OK: {len(result.questions)} question(s) checked.")
    return 0


def _report(problems: Sequence[Problem]) -> None:
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"{len(problems)} problem(s) found.", file=sys.stderr)


def extract(export: Path, into: Path) -> int:
    """Write the questions of a Moodle export as question sources into the collection."""
    collection = Collection.find(into)
    written = extract_sources(collection, export.read_text(encoding="utf-8"), str(export))
    for path in written:
        print(f"Wrote {collection.relative(path)}")
    print(f"Extracted {len(written)} question(s) into {collection.root}")
    return 0


def preview(paths: Sequence[Path], output: Path) -> int:
    """Write an HTML page showing the selected questions; problems are listed on the page too."""
    collection = open_collection(paths)
    result = validate(collection, paths)
    output.write_text(preview_page(collection, result.questions, result.problems), encoding="utf-8")
    print(f"Wrote a preview of {len(result.questions)} question(s) to {output}")
    if result.problems:
        _report(result.problems)
        return 1
    return 0
