"""The commands: generate, extract, check, preview."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from moodle_qc.collection import Collection
from moodle_qc.convert import import_file, load_question
from moodle_qc.extract import extract as extract_sources


def open_collection(paths: Sequence[Path], root_category: str | None = None) -> Collection:
    collection = Collection.find(paths[0])
    collection.root_category_override = root_category
    return collection


def generate(paths: Sequence[Path], output: Path, root_category: str | None = None) -> int:
    """Write one import file for the selected question sources."""
    collection = open_collection(paths, root_category)
    questions = [load_question(collection, path) for path in collection.sources(paths)]
    output.write_text(import_file(collection, questions), encoding="utf-8")
    print(f"Wrote {len(questions)} question(s) to {output}")
    return 0


def extract(export: Path, into: Path) -> int:
    """Write the questions of a Moodle export as question sources into the collection."""
    collection = Collection.find(into)
    written = extract_sources(collection, export.read_text(encoding="utf-8"), str(export))
    for path in written:
        print(f"Wrote {collection.relative(path)}")
    print(f"Extracted {len(written)} question(s) into {collection.root}")
    return 0
