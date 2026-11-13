"""Question sources: Markdown files with YAML front matter.

Layout::

    ---
    type: sc
    points: 2
    ---
    # Question name

    Question text in Markdown.

    ## Answers
    - [ ] A wrong answer
      > Feedback for this answer
    - [x] {50%} The correct answer

    ## Solution
    Grading information (Moodle's general feedback).

    ## Notes
    Private remarks, never generated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from moodle_qc.errors import UserError
from moodle_qc.markdown import split_blocks

SECTIONS = ("Answers", "Solution", "Notes")

_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
_SECTION = re.compile(r"^## (Answers|Solution|Notes)\s*$")
_HEADING = re.compile(r"^# (.+)$")
_ANSWER = re.compile(r"^- \[( |x|X)\] (?:\{(-?\d+(?:\.\d+)?)%\} )?(.*)$")
_FENCE = re.compile(r"^```")

FRONT_MATTER_ORDER = (
    "type",
    "id",
    "name",
    "category",
    "lang",
    "points",
    "penalty",
    "shuffle",
    "tags",
    "multiple",
    "numbering",
    "scoring",
    "labels",
    "deduction",
    "distractors",
    "reusable",
    "feedback",
    "show_num_correct",
    "show_instruction",
)


@dataclass
class Answer:
    """One answer of a choice question."""

    text: str
    correct: bool
    feedback: str = ""
    fraction: float | None = None
    """Explicit percentage (``{50%}``), else computed by the question type."""


@dataclass
class SourceDocument:
    """The parsed content of one question source file."""

    front_matter: dict[str, Any] = field(default_factory=dict)
    heading: str | None = None
    """The first ``# heading``: the question name unless the front matter sets ``name``."""
    text: str = ""
    answers: list[Answer] | None = None
    solution: str = ""
    notes: str = ""


def parse_source(content: str, origin: str = "question source") -> SourceDocument:
    """Parse a question source; raises ``UserError`` naming ``origin`` on malformed input."""
    content = content.replace("\r\n", "\n")
    front_matter: dict[str, Any] = {}
    match = _FRONT_MATTER.match(content)
    if match:
        try:
            loaded = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as error:
            raise UserError(f"{origin}: invalid front matter: {error}") from None
        if not isinstance(loaded, dict):
            raise UserError(f"{origin}: front matter must be a mapping of settings.")
        front_matter = loaded
        content = content[match.end() :]

    sections = _split_sections(content)
    body = sections.get("", "")
    heading = None
    first, _, rest = body.lstrip("\n").partition("\n")
    heading_match = _HEADING.match(first)
    if heading_match:
        heading = heading_match.group(1).strip()
        body = rest
    answers = None
    if "Answers" in sections:
        answers = _parse_answers(sections["Answers"], origin)
    return SourceDocument(
        front_matter=front_matter,
        heading=heading,
        text=body.strip("\n"),
        answers=answers,
        solution=sections.get("Solution", "").strip("\n"),
        notes=sections.get("Notes", "").strip("\n"),
    )


def format_source(document: SourceDocument) -> str:
    """Write a question source in its canonical layout."""
    parts: list[str] = []
    front_matter = {key: document.front_matter[key] for key in _ordered(document.front_matter)}
    if front_matter:
        dumped = yaml.dump(
            front_matter,
            Dumper=_FrontMatterDumper,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=1000,
        )
        parts.append(f"---\n{dumped}---")
    if document.heading:
        parts.append(f"# {document.heading}")
    if document.text:
        parts.append(document.text)
    if document.answers is not None:
        parts.append("## Answers\n" + "\n".join(_format_answer(a) for a in document.answers))
    if document.solution:
        parts.append(f"## Solution\n\n{document.solution}")
    if document.notes:
        parts.append(f"## Notes\n\n{document.notes}")
    return "\n\n".join(parts) + "\n"


class _FrontMatterDumper(yaml.SafeDumper):
    """Mappings as blocks, lists inline (``tags: [26hs]``)."""


def _represent_list(dumper: yaml.SafeDumper, data: list[Any]) -> yaml.Node:
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


_FrontMatterDumper.add_representer(list, _represent_list)


def _ordered(front_matter: dict[str, Any]) -> list[str]:
    known = [key for key in FRONT_MATTER_ORDER if key in front_matter]
    return known + sorted(key for key in front_matter if key not in FRONT_MATTER_ORDER)


def _split_sections(content: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"": []}
    current = ""
    in_fence = False
    for line in content.split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
        match = None if in_fence else _SECTION.match(line)
        if match:
            current = match.group(1)
            sections[current] = []
        else:
            sections[current].append(line)
    return {name: "\n".join(lines) for name, lines in sections.items()}


def _parse_answers(section: str, origin: str) -> list[Answer]:
    answers: list[Answer] = []
    for block in split_blocks(section):
        for line in block:
            match = _ANSWER.match(line)
            if match:
                fraction = float(match.group(2)) if match.group(2) is not None else None
                answers.append(Answer(match.group(3), match.group(1) != " ", fraction=fraction))
            elif answers and (line.startswith("  > ") or line == "  >"):
                feedback = line[4:] if len(line) > 3 else ""
                last = answers[-1]
                last.feedback = f"{last.feedback}\n{feedback}" if last.feedback else feedback
            elif answers and line.startswith("  "):
                answers[-1].text += "\n" + line[2:]
            else:
                raise UserError(
                    f"{origin}: can't read answer line {line!r}; "
                    "answers are written as '- [ ] text' or '- [x] text'."
                )
    return answers


def _format_answer(answer: Answer) -> str:
    mark = "x" if answer.correct else " "
    fraction = f"{{{_number(answer.fraction)}%}} " if answer.fraction is not None else ""
    lines = [f"- [{mark}] {fraction}{answer.text.replace(chr(10), chr(10) + '  ')}"]
    lines.extend(f"  > {line}".rstrip() for line in answer.feedback.split("\n") if answer.feedback)
    return "\n".join(lines)


def _number(value: float) -> str:
    return f"{value:.7f}".rstrip("0").rstrip(".")
