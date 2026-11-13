# moodle-qc

Command-line tool that converts Markdown question sources to Moodle XML import files and back. Implementation follows the GitHub issues (#1 … #13).

Read before working:

- `CONTEXT.md` – the glossary. Use its terms in code, tests, docs and conversation; avoid the words listed under _Avoid_.
- `docs/adr/` – decisions that must not be undone without a new ADR.
- `docs/spec-moodle-qc-v1.md` – the spec for the first version (user stories, modules, testing decisions, out of scope).
- `docs/moodle-format-notes.md` – verified facts about Moodle XML per question type, categories and import behaviour.
- `tests/fixtures/moodle/` – real Moodle XML from `moodle.assessment.fhnw.ch`:
  - `moodle-xml-reference.xml` – hand-built `multichoice`, `kprime`, `mtf`, `sc` with nested categories; `moodle-xml-reference.reexport.xml` is Moodle's export after importing it.
  - `sample-ddwtos.xml` – hand-written import file (two gap questions, gap groups, code blocks); `sample-ddwtos-export.xml` – Moodle's export of the second one after manual edits.
  - `sample-ddimageortext.xml` – real export with embedded PNG (not a v1 type: use it for raw question source round trips).

Conventions:

- Python. Distributed as a Docker image and via this repo (no PyPI).
- Tests on two levels: unit tests at each module's public interface, and integration tests that run the commands (`generate`, `extract`, `check`, `preview`) in-process on temporary folders. Compare Moodle XML by content, not formatting.
- Write text into Moodle XML as CDATA, not XML escaping.

Development (uv): `uv sync`, then `uv run pytest`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format .`. Code lives in `src/moodle_qc/`; tests in `tests/unit/` (module interfaces) and `tests/integration/` (commands in-process). `tests/support/moodle_xml_compare.py` compares Moodle XML by content: use `assert_moodle_xml_equal` in integration and round-trip tests.
