"""Command-line entry point of the question converter."""

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version

PROG = "moodle-qc"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Question converter: generate Moodle XML import files from Markdown "
            "question sources, and extract Moodle exports back into question sources."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {version(PROG)}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line with ``argv`` and return the exit code."""
    parser = _parser()
    try:
        parser.parse_args(argv)
    except SystemExit as exit_:
        return exit_.code if isinstance(exit_.code, int) else 1
    parser.print_help()
    return 0


def run() -> None:
    """Console script entry point."""
    sys.exit(main())
