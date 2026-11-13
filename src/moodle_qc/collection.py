"""The question collection: finding its root, reading its collection config, merging settings."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from moodle_qc.errors import UserError
from moodle_qc.markdown import code_style

CONFIG_NAME = "moodle-qc.yaml"

BUILTIN_DEFAULTS: dict[str, Any] = {
    "lang": "de",
    "points": 1,
    "penalty": 0.3333333,
    "shuffle": True,
    "tags": [],
    "feedback": {"correct": "", "partially": "", "incorrect": ""},
    "show_num_correct": True,
}
"""Settings every question starts with."""

BUILTIN_TYPE_DEFAULTS: dict[str, dict[str, Any]] = {
    "sc": {"scoring": "sconezero", "numbering": "none"},
    "multichoice": {"numbering": "abc", "show_instruction": False},
    "kprime": {"scoring": "kprime", "labels": ["True", "False"]},
    "mtf": {
        "scoring": "subpoints",
        "labels": ["True", "False"],
        "numbering": "none",
        "deduction": 0,
    },
    "ddwtos": {},
    "raw": {},
}
"""Per question type defaults, before the collection config's ``types`` section."""

_CONFIG_KEYS = {"root_category", "allowed_types", "code_line_height", "defaults", "types"}
_COMBINED_KEYS = {"tags"}
_MERGED_MAPPINGS = {"feedback"}


@dataclass
class Collection:
    """A folder tree of question sources with ``moodle-qc.yaml`` at its root."""

    root: Path
    config: dict[str, Any] = field(default_factory=dict)
    root_category_override: str | None = None

    @classmethod
    def find(cls, start: Path) -> Collection:
        """Find the collection root: the nearest folder at or above ``start`` with the config."""
        start = start.resolve()
        folder = start if start.is_dir() else start.parent
        for candidate in (folder, *folder.parents):
            config_file = candidate / CONFIG_NAME
            if config_file.is_file():
                return cls(candidate, _load_config(config_file))
        raise UserError(f"No {CONFIG_NAME} found in {folder} or any folder above it.")

    @property
    def root_category(self) -> str | None:
        value = self.root_category_override or self.config.get("root_category")
        return str(value).strip("/") if value else None

    @property
    def allowed_types(self) -> set[str] | None:
        types = self.config.get("allowed_types")
        return {str(t) for t in types} if types else None

    @property
    def pre_style(self) -> str:
        return code_style(self.config.get("code_line_height", 1.2))

    def defaults_for(self, qtype: str) -> dict[str, Any]:
        """Settings of a question of ``qtype`` before its own front matter."""
        return merge_settings(
            BUILTIN_DEFAULTS,
            BUILTIN_TYPE_DEFAULTS.get(qtype, {}),
            self.config.get("defaults") or {},
            (self.config.get("types") or {}).get(qtype) or {},
        )

    def settings_for(self, qtype: str, front_matter: Mapping[str, Any]) -> dict[str, Any]:
        return merge_settings(self.defaults_for(qtype), front_matter)

    def relative(self, path: Path) -> PurePosixPath:
        try:
            return PurePosixPath(path.resolve().relative_to(self.root).as_posix())
        except ValueError:
            raise UserError(f"{path} is not inside the question collection {self.root}.") from None

    def sources(self, selection: Iterable[Path]) -> list[Path]:
        """Question sources (``.md`` files) in the selected files and folders, sorted by path."""
        found: set[Path] = set()
        for path in selection:
            path = path.resolve()
            if path.is_dir():
                found.update(p for p in path.rglob("*.md") if not _hidden(p, self.root))
            elif path.suffix == ".md" and path.is_file() and not _hidden(path, self.root):
                found.add(path)
            elif not path.exists():
                raise UserError(f"{path} does not exist.")
            else:
                raise UserError(f"{path} is not a question source (.md) or folder.")
        for path in found:
            self.relative(path)
        return sorted(found, key=lambda p: self.relative(p).as_posix())


def merge_settings(*layers: Mapping[str, Any]) -> dict[str, Any]:
    """Later layers override earlier ones; tags are combined and feedback texts merged by key."""
    merged: dict[str, Any] = {}
    for layer in layers:
        for key, value in layer.items():
            if key in _COMBINED_KEYS:
                merged[key] = list(dict.fromkeys([*merged.get(key, []), *(value or [])]))
            elif key in _MERGED_MAPPINGS and isinstance(value, Mapping):
                merged[key] = {**merged.get(key, {}), **value}
            else:
                merged[key] = value
    return merged


def _load_config(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        raise UserError(f"{path}: invalid YAML: {error}") from None
    if not isinstance(loaded, dict):
        raise UserError(f"{path}: expected a mapping of settings.")
    unknown = set(loaded) - _CONFIG_KEYS
    if unknown:
        raise UserError(f"{path}: unknown setting(s) {', '.join(sorted(unknown))}.")
    return loaded


def _hidden(path: Path, root: Path) -> bool:
    """Hidden folders/files and READMEs are not question sources."""
    if path.name.lower() == "readme.md":
        return True
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    return any(part.startswith(".") for part in parts)
