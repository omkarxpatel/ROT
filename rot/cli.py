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
    parser.add_argument(
        "file",
        nargs="?",
        help=".rot source file to run (omit to start an interactive REPL)",
    )
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
    parser.add_argument(
        "--vm",
        action="store_true",
        help=(
            "run via the bytecode VM (Milestone 2). The tree-walking "
            "interpreter is still the default; --vm opts into the "
            "compiled path. Some statements (class, try/catch, throw, "
            "import, member access, slicing) aren't codegen'd yet — "
            "the VM will report a clear error if you hit one."
        ),
    )
    parser.add_argument(
        "--repl",
        action="store_true",
        help="start the interactive REPL (equivalent to invoking with no file)",
    )
    return parser


def _run_via_vm(compiler: Compiler, source: str) -> None:
    """Drive the M2 bytecode path: parse → codegen → VM run.

    The VM's globals are pre-populated with the same builtins the
    tree-walker exposes — `cout`/`coutln` from `rot.interpreter`
    (which route to stdout when no Interpreter is active) plus the
    rest of the standard library from `rot.builtins`. Together
    these make `--vm` runnable on any program whose statements the
    codegen supports.
    """
    from .builtins import BUILTINS
    from .codegen import Compiler as VMCompiler
    from .interpreter import _builtin_cout, _builtin_coutln
    from .vm import VM

    program = compiler.parse(source)
    vm_builtins: dict = dict(BUILTINS)
    vm_builtins["cout"] = _builtin_cout
    vm_builtins["coutln"] = _builtin_coutln
    chunk = VMCompiler().compile(program)
    VM(chunk, builtins=vm_builtins).run()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # No file given (or --repl) → drop into REPL.
    if args.repl or args.file is None:
        from .repl import start_repl
        start_repl()
        return

    source_path = pathlib.Path(args.file)
    if source_path.suffix != ".rot":
        parser.error(f"file must be a .rot file (got {args.file})")

    try:
        source = source_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        parser.error(f"file not found: {args.file}")
    except IsADirectoryError:
        parser.error(f"is a directory, not a file: {args.file}")
    except PermissionError:
        parser.error(f"permission denied: {args.file}")
    except UnicodeDecodeError as e:
        parser.error(f"{args.file} is not valid UTF-8: {e.reason}")
    except OSError as e:
        parser.error(f"cannot read {args.file}: {e}")

    try:
        compiler = Compiler(trace=args.trace)
        if args.no_run:
            compiler.parse(source)
            if not args.trace:
                print(f"OK — {args.file} parsed cleanly.")
            return
        if args.vm:
            _run_via_vm(compiler, source)
            return
        compiler.run(source, source_path=str(source_path))
    except RotError as err:
        # v2.22.7: render in rustc-style — header + source line + caret.
        # When the error has no location, ``format`` returns the bare
        # ``error: <msg>`` form. Source and filename are threaded so the
        # block can pull the right line.
        print(err.format(source, args.file), file=sys.stderr)
        sys.exit(1)
