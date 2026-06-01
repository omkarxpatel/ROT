"""Tests for `VM.iter_execute()` — the step-mode entry point used by
the playground's opcode-level visualization (Milestone 3).

These tests exercise the snapshot stream itself rather than the final
VM state. The ordinary `run()` path is covered exhaustively by
`tests/test_vm.py`; here we verify shape, ordering, IP transitions,
chunk_id tracking, frame depth, output capture, and error handling.
"""

import contextlib
import io

from rot.builtins import BUILTINS
from rot.codegen import Compiler
from rot.interpreter import _builtin_cout, _builtin_coutln
from rot.lexer import Lexer
from rot.syntax import Parser
from rot.vm import VM, VMSnapshot


def _step(source: str, *, with_builtins: bool = False) -> list[VMSnapshot]:
    """Compile and step-execute `source`. Returns the snapshot list.

    When `with_builtins=True`, the standard library + cout/coutln are
    installed so the test source can print. The cli's --vm path does
    the same wiring.
    """
    program = Parser(Lexer().tokenize(source)).parse()
    chunk = Compiler().compile(program)
    builtins = None
    if with_builtins:
        builtins = dict(BUILTINS)
        builtins["cout"] = _builtin_cout
        builtins["coutln"] = _builtin_coutln
    vm = VM(chunk, builtins=builtins)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return list(vm.iter_execute(capture=buf))


# ─── Shape: assignment ────────────────────────────────────────────


def test_assignment_yields_load_const_then_store_name():
    snaps = _step("x = 5")
    # Compiler emits a trailing RETURN for the top-level chunk.
    ops = [s.op_name for s in snaps]
    assert ops[:2] == ["LOAD_CONST", "STORE_NAME"]
    assert ops[-1] == "RETURN"
    # LOAD_CONST pushes; STORE_NAME pops + binds.
    assert snaps[0].stack == ["5"]
    assert snaps[1].stack == []
    # Final globals view shows the user binding.
    assert snaps[-1].globals_view == {"x": "5"}


def test_addition_yields_two_loads_then_add_then_store():
    snaps = _step("y = 2 + 3")
    ops = [s.op_name for s in snaps]
    assert ops[:4] == ["LOAD_CONST", "LOAD_CONST", "ADD", "STORE_NAME"]
    # After both loads but before ADD: stack has [2, 3].
    assert snaps[1].stack == ["2", "3"]
    # ADD popped both, pushed 5.
    assert snaps[2].stack == ["5"]
    # STORE_NAME cleared the stack and bound the global.
    assert snaps[-1].globals_view == {"y": "5"}


def test_ip_advances_monotonically_outside_jumps():
    snaps = _step("a = 1\nb = 2")
    # No branches — IP should march upward across all snapshots.
    ips = [s.ip for s in snaps]
    assert ips == sorted(ips)
    assert ips[0] > 0


# ─── Line attribution ─────────────────────────────────────────────


def test_line_field_tracks_source_position():
    snaps = _step("a = 1\n\nb = 2")
    lines = sorted({s.line for s in snaps if s.line})
    # Both real source lines should appear in the trace (1 and 3),
    # not the blank line 2.
    assert lines == [1, 3]


# ─── Chunk id + frame depth across CALL / RETURN_VALUE ─────────────


def test_call_swaps_chunk_id_and_increments_frame_depth():
    src = "funct sq(x) { return x * x }\nr = sq(4)"
    snaps = _step(src)
    chunk_ids = [s.chunk_id for s in snaps]
    # The top-level chunk is "main"; inside sq's body it's "sq".
    assert "main" in chunk_ids
    assert "sq" in chunk_ids
    # Frame depth flips between 0 and 1 across the call boundary.
    depths = {s.frame_depth for s in snaps}
    assert depths == {0, 1}
    # Final binding lives at the top.
    assert snaps[-1].globals_view.get("r") == "16"


def test_recursive_call_pushes_frames_progressively():
    src = (
        "funct fac(n) {\n"
        "    if (n <= 1) { return 1 }\n"
        "    return n * fac(n - 1)\n"
        "}\n"
        "r = fac(3)"
    )
    snaps = _step(src)
    # Three nested calls — the recursion goes 3 → 2 → 1.
    max_depth = max(s.frame_depth for s in snaps)
    assert max_depth == 3
    assert snaps[-1].globals_view.get("r") == "6"


# ─── Output capture ────────────────────────────────────────────────


def test_cout_output_is_captured_per_opcode():
    snaps = _step('coutln("hi")', with_builtins=True)
    # Exactly one snapshot should report the print.
    outputs = [s.output_since_last for s in snaps if s.output_since_last]
    assert outputs == ["hi\n"]


def test_multiple_couts_attribute_to_their_own_snapshots():
    snaps = _step(
        'coutln("a")\ncoutln("b")', with_builtins=True
    )
    outputs = [s.output_since_last for s in snaps if s.output_since_last]
    assert outputs == ["a\n", "b\n"]


# ─── Halting / errors ──────────────────────────────────────────────


def test_terminal_snapshot_marks_halted():
    snaps = _step("x = 1")
    # The final snapshot — whichever it is — must claim the halt.
    assert snaps[-1].halted is True
    # No earlier snapshot should claim halt.
    assert not any(s.halted for s in snaps[:-1])


def test_uncaught_throw_yields_error_then_stops():
    snaps = _step('throw "bad"')
    last = snaps[-1]
    assert last.error is not None
    assert "bad" in last.error
    assert last.halted is True


def test_caught_throw_continues_into_handler():
    src = (
        'try {\n'
        '    throw "boom"\n'
        '} catch (e) {\n'
        '    msg = e\n'
        '}'
    )
    snaps = _step(src)
    # The throw fires, then execution lands in the catch and binds.
    assert snaps[-1].globals_view.get("msg") == "boom"
    assert snaps[-1].error is None


# ─── to_dict shape ────────────────────────────────────────────────


def test_snapshot_to_dict_is_json_safe():
    import json

    snaps = _step("x = 1")
    dumped = json.dumps([s.to_dict() for s in snaps])
    # Round-trips through JSON without losing structure.
    parsed = json.loads(dumped)
    assert isinstance(parsed, list)
    assert all("op_name" in d for d in parsed)
    assert parsed[-1]["halted"] is True
