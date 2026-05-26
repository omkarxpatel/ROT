"""End-to-end golden tests: every examples/*.rot file is lexed, parsed,
exec'd, and its captured stdout compared to the matching *.expected file."""

import contextlib
import io
import pathlib

import pytest

from rot.lexer import Lexer
from rot.parser import Parser


EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"


def _examples_with_expected():
    return sorted(p for p in EXAMPLES.glob("*.rot") if p.with_suffix(".expected").exists())


@pytest.mark.parametrize("rot_file", _examples_with_expected(), ids=lambda p: p.stem)
def test_example_produces_expected_output(rot_file: pathlib.Path):
    expected = rot_file.with_suffix(".expected").read_text()
    source = rot_file.read_text()

    with contextlib.redirect_stdout(io.StringIO()):
        tokens = Lexer().tokenize(source)
        python_code = Parser().parse(tokens)

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        exec(python_code, {})

    assert captured.getvalue() == expected
