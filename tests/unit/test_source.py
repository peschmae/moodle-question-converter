import pytest

from moodle_qc.errors import UserError
from moodle_qc.source import Answer, SourceDocument, format_source, parse_source

SOURCE = """---
type: sc
points: 2
---

# Error Budget

Was beschreibt ein **Error Budget**?

## Answers
- [ ] Das Budget für Monitoring.
  > Nein, es geht um Zuverlässigkeit.
- [x] {50%} Die erlaubte Unzuverlässigkeit.

## Solution

1 − SLO.

## Notes

Aus der Prüfung 25HS.
"""


def test_parses_front_matter_title_text_answers_solution_and_notes() -> None:
    document = parse_source(SOURCE)

    assert document == SourceDocument(
        front_matter={"type": "sc", "points": 2},
        title="Error Budget",
        text="Was beschreibt ein **Error Budget**?",
        answers=[
            Answer("Das Budget für Monitoring.", False, "Nein, es geht um Zuverlässigkeit."),
            Answer("Die erlaubte Unzuverlässigkeit.", True, fraction=50.0),
        ],
        solution="1 − SLO.",
        notes="Aus der Prüfung 25HS.",
    )


def test_canonical_source_is_written_back_unchanged() -> None:
    assert format_source(parse_source(SOURCE)) == SOURCE


def test_section_headings_inside_code_blocks_are_question_text() -> None:
    document = parse_source("# Q\n\n```\n## Answers\n```\n")

    assert document.text == "```\n## Answers\n```"
    assert document.answers is None


def test_without_title_the_text_starts_right_away() -> None:
    document = parse_source("---\ntype: sc\n---\nNur Text.\n")

    assert document.title is None
    assert document.text == "Nur Text."


def test_malformed_answer_line_names_the_file() -> None:
    with pytest.raises(UserError, match=r"sw09/q\.md: can't read answer line '\* falsch'"):
        parse_source("# Q\n\n## Answers\n* falsch\n", "sw09/q.md")
