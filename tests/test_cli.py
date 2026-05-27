"""Tests for the command-line entry point (rot/cli.py).

Drives the CLI by spawning a subprocess (`python -m rot ...`) and inspecting
stdout / stderr / exit code. This isolates argparse, the `.rot` extension
check, file-not-found handling, permission errors, the `--trace` / `--no-run`
/ `--version` / `--repl` flags, and the rustc-style error rendering on
RotError.

Corresponds to bug-audit T82-T89 plus a handful of related edges.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

from rot import __version__


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _run_cli(args, *, input=None, cwd=None):
    """Helper: spawn `python -m rot <args>` and return the CompletedProcess."""
    return subprocess.run(
        [sys.executable, "-m", "rot", *args],
        capture_output=True,
        text=True,
        input=input,
        cwd=str(cwd if cwd is not None else REPO_ROOT),
    )


# --- T84: --version prints `rot <version>` ---

def test_cli_version_prints_rot_version_string():
    proc = _run_cli(["--version"])
    assert proc.returncode == 0
    # argparse prints --version on stdout (Python 3.4+).
    assert proc.stdout.strip() == f"rot {__version__}"


# --- T87: file not found ---

def test_cli_missing_file_exits_with_argparse_error(tmp_path: pathlib.Path):
    # parser.error() exits with code 2 (argparse standard) and writes to stderr.
    bogus = tmp_path / "no_such.rot"
    proc = _run_cli([str(bogus)])
    assert proc.returncode != 0
    # The error message must mention the missing path so the user knows
    # what to fix.
    assert str(bogus) in proc.stderr
    assert "not found" in proc.stderr.lower()


# --- T86: non-.rot extension rejected ---

def test_cli_non_rot_extension_rejected(tmp_path: pathlib.Path):
    bad = tmp_path / "foo.txt"
    bad.write_text('cout("hi")')
    proc = _run_cli([str(bad)])
    assert proc.returncode != 0
    assert ".rot file" in proc.stderr
    assert str(bad) in proc.stderr


# --- T82: --no-run validates without executing ---

def test_cli_no_run_does_not_execute_program(tmp_path: pathlib.Path):
    # A program that would print "RAN" if executed. --no-run should parse
    # only and never emit the output.
    rot = tmp_path / "p.rot"
    rot.write_text('coutln("RAN")\n')
    proc = _run_cli(["--no-run", str(rot)])
    assert proc.returncode == 0
    # The "RAN" never appears because the program was never interpreted.
    assert "RAN" not in proc.stdout
    # The parse-cleanly marker should appear on success.
    assert "OK" in proc.stdout


# --- T83 / T90: --trace produces tokenizer trace output ---

def test_cli_trace_emits_tokenizer_trace(tmp_path: pathlib.Path):
    rot = tmp_path / "p.rot"
    rot.write_text('coutln("x")\n')
    proc = _run_cli(["--trace", str(rot)])
    assert proc.returncode == 0
    # The trace prints sectioned headers — `Process 1 - Tokenizer`, etc.
    # See `rot/compiler.py`.
    assert "Tokenizer" in proc.stdout
    assert "Parser" in proc.stdout
    # And the token kinds for `coutln(...)`.
    assert "PRINTLN" in proc.stdout
    assert "L_PAREN" in proc.stdout
    assert "STRING_LIT" in proc.stdout


# --- T88: RotError in source → exit 1, stderr has rustc-style block ---

def test_cli_rot_error_exits_with_rustc_style_block(tmp_path: pathlib.Path):
    # Runtime undefined-name error. v2.22.7 renders this as a rustc-style
    # block on stderr.
    rot = tmp_path / "bad.rot"
    rot.write_text("cout(undef)\n")
    proc = _run_cli([str(rot)])
    assert proc.returncode == 1
    # Rustc-style header — `error: <msg>` and `--> file:line:col`.
    assert "error:" in proc.stderr
    assert f"--> {rot}:" in proc.stderr
    # Caret line should be present too.
    assert "^" in proc.stderr


# --- T89: default REPL when no file ---

def test_cli_no_file_starts_repl_and_exits_on_eof():
    # Feeding EOF immediately should let the REPL print its banner and exit
    # cleanly with code 0. The banner identifies the REPL by `REPL`.
    proc = _run_cli([], input="")
    assert proc.returncode == 0
    assert "REPL" in proc.stdout


# --- T85: --repl flag explicit ---

def test_cli_repl_flag_starts_repl_explicitly():
    # Same shape as the no-file case — the banner must appear and EOF exits
    # cleanly.
    proc = _run_cli(["--repl"], input="")
    assert proc.returncode == 0
    assert "REPL" in proc.stdout


# --- v2.14.8: PermissionError on source file is a clean error ---

@pytest.mark.skipif(
    os.name == "nt", reason="chmod-based perm test doesn't apply on Windows"
)
def test_cli_permission_denied_on_source_is_clean_error(tmp_path: pathlib.Path):
    rot = tmp_path / "p.rot"
    rot.write_text('coutln("ok")\n')
    rot.chmod(0o000)
    try:
        proc = _run_cli([str(rot)])
        assert proc.returncode != 0
        # The CLI's PermissionError branch surfaces "permission denied".
        # On macOS / Linux this works; running as root would bypass and
        # the file would just be readable — the skipif above guards against
        # that on Windows but not root. Accept either form ("permission
        # denied" or "cannot read") to keep the assertion tolerant.
        msg = proc.stderr.lower()
        assert "permission" in msg or "cannot read" in msg
    finally:
        # Restore so pytest can clean up the tmp_path.
        rot.chmod(0o644)


# --- v2.20.5: UTF-8 BOM at start of source is accepted ---

def test_cli_utf8_bom_in_source_is_silently_accepted(tmp_path: pathlib.Path):
    # A leading BOM (`﻿`) is sometimes added by Windows tooling. The
    # CLI's `read_text(encoding="utf-8")` and the lexer must accept it
    # without producing an error.
    rot = tmp_path / "bom.rot"
    # Write raw bytes to make the BOM verbatim.
    rot.write_bytes(b"\xef\xbb\xbfcoutln(\"hi\")\n")
    proc = _run_cli([str(rot)])
    assert proc.returncode == 0
    assert proc.stdout.strip() == "hi"
