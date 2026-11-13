"""Command-line entry point of the question converter."""

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

from moodle_qc import commands
from moodle_qc.errors import UserError

PROG = "moodle-qc"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Question converter: generate Moodle XML import files from Markdown "
            "question sources, and extract Moodle exports back into question sources."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {version(PROG)}")
    subcommands = parser.add_subparsers(dest="command", metavar="command")

    generate = subcommands.add_parser(
        "generate", help="turn question sources into one Moodle XML import file"
    )
    generate.add_argument("paths", nargs="+", type=Path, help="question sources or folders")
    generate.add_argument(
        "-o", "--output", type=Path, default=Path("moodle-import.xml"), help="import file to write"
    )
    _add_root_category(generate)

    extract = subcommands.add_parser(
        "extract", help="turn a Moodle XML export into question sources"
    )
    extract.add_argument("export", type=Path, help="Moodle XML export file")
    extract.add_argument(
        "--into", type=Path, default=Path("."), help="folder inside the question collection"
    )
    return parser


def _add_root_category(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root-category", help="put all categories below this one (overrides the config)"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line with ``argv`` and return the exit code."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:
        return exit_.code if isinstance(exit_.code, int) else 1
    try:
        if args.command == "generate":
            return commands.generate(args.paths, args.output, args.root_category)
        if args.command == "extract":
            return commands.extract(args.export, args.into)
    except UserError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    parser.print_help()
    return 0


def run() -> None:
    """Console script entry point."""
    sys.exit(main())
