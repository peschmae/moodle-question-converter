# moodle-qc

Keep Moodle questions as Markdown files in git and convert them to Moodle XML for import, and Moodle exports back to Markdown.

Status: in development, following the GitHub issues. Design: `docs/spec-moodle-qc-v1.md`.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                    # install dependencies
uv run pytest              # run all tests
uv run mypy                # type-check
uv run ruff check .        # lint
uv run ruff format .       # format
uv run moodle-qc --help    # run the command
```
