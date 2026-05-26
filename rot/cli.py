"""Command-line entry point: `python -m rot <file.rot> [flags]`."""

from __future__ import annotations

import argparse
import pathlib
import sys

from . import __version__
from .compiler import Compiler
from .errors import RotError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rot",
        description="ROT language — runs .rot files directly via the tree-walking interpreter.",
    )
    parser.add_argument("file", help=".rot source file to run")
    parser.add_argument(
        "--version",
        action="version",
        version=f"rot {__version__}",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="dump tokenizer/parser tables to stdout",
    )
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="parse only — validate the program without interpreting it",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    source_path = pathlib.Path(args.file)
    if source_path.suffix != ".rot":
        parser.error(f"file must be a .rot file (got {args.file})")

    try:
        source = source_path.read_text()
    except FileNotFoundError:
        parser.error(f"file not found: {args.file}")

    try:
        compiler = Compiler(trace=args.trace)
        if args.no_run:
            compiler.parse(source)
            if not args.trace:
                print(f"OK — {args.file} parsed cleanly.")
            return
        compiler.run(source)
    except RotError as err:
        print(f"rot error: {err}", file=sys.stderr)
        sys.exit(1)
