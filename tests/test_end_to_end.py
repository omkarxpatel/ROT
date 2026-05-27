"""End-to-end golden tests: every examples/*.rot file is interpreted
and its captured stdout compared to the matching *.expected file."""

import contextlib
import io
import pathlib
import subprocess
import sys

import pytest

from rot.compiler import Compiler


EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _examples_with_expected():
    return sorted(p for p in EXAMPLES.glob("*.rot") if p.with_suffix(".expected").exists())


@pytest.mark.parametrize("rot_file", _examples_with_expected(), ids=lambda p: p.stem)
def test_example_produces_expected_output(rot_file: pathlib.Path):
    expected = rot_file.with_suffix(".expected").read_text()
    source = rot_file.read_text()

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        Compiler(trace=False).run(source, source_path=str(rot_file))

    assert captured.getvalue() == expected


def test_cli_renders_rustc_style_error_for_syntax_error(tmp_path: pathlib.Path):
    """v2.22.7: a CLI invocation on a .rot file with a syntax error prints
    the rustc-style rendering on stderr — header, file:line:col anchor,
    numbered source line, caret line."""
    rot_file = tmp_path / "bad.rot"
    rot_file.write_text("x = 1\ny = 2 +\n")
    proc = subprocess.run(
        [sys.executable, "-m", "rot", str(rot_file)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode != 0
    stderr = proc.stderr
    assert "error: " in stderr
    assert f"--> {rot_file}:" in stderr
    # The numbered source line and caret should appear.
    assert "| y = 2 +" in stderr
    assert "^" in stderr


def test_cli_renders_rustc_style_error_for_runtime_error(tmp_path: pathlib.Path):
    """A runtime error (undefined name) on a CLI run also renders the
    rustc-style block — the line/col are threaded from the AST."""
    rot_file = tmp_path / "bad.rot"
    rot_file.write_text("a = 1\nb = 2\ncout(undef)\n")
    proc = subprocess.run(
        [sys.executable, "-m", "rot", str(rot_file)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode != 0
    stderr = proc.stderr
    assert "error: name 'undef' is not defined" in stderr
    assert f"--> {rot_file}:3:" in stderr
    assert "| cout(undef)" in stderr
