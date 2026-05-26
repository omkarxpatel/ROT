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
        description="ROT language compiler — transpiles .rot files to Python and runs them.",
    )
    parser.add_argument("file", help=".rot source file to compile")
    parser.add_argument(
        "--version",
        action="version",
        version=f"rot {__version__}",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="dump tokenizer/parser pipeline tables to stdout",
    )
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="transpile only — don't execute the generated Python",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output.py",
        help="path to write the generated Python (default: output.py)",
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
        python_code = compiler.compile(source)
        compiler.save(python_code, args.output)
        if args.no_run:
            if not args.trace:
                print(f"wrote {args.output}")
            return
        compiler.execute(python_code)
    except RotError as err:
        print(f"rot error: {err}", file=sys.stderr)
        sys.exit(1)
