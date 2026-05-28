"""Tests for the bytecode compiler (rot/codegen.py).

M2 foundation: covers the opcodes the v2.27.0 codegen emits —
literals, identifiers, simple assigns/let-bindings, arithmetic.
Later Z's extend the set; each adds tests here.
"""

import pytest

from rot.codegen import Chunk, Compiler
from rot.errors import InterpreterError
from rot.lexer import Lexer
from rot.opcodes import Op
from rot.syntax import Parser


def _compile(source: str) -> Chunk:
    program = Parser(Lexer().tokenize(source)).parse()
    return Compiler().compile(program)


# ─── Chunk helpers ───────────────────────────────────────────────


def test_chunk_dedupes_constants_by_equality():
    chunk = Chunk()
    a = chunk.add_const(5)
    b = chunk.add_const(5)
    c = chunk.add_const("hi")
    d = chunk.add_const("hi")
    assert a == b == 0
    assert c == d == 1
    assert chunk.constants == [5, "hi"]


def test_chunk_dedupes_names():
    chunk = Chunk()
    assert chunk.add_name("x") == 0
    assert chunk.add_name("y") == 1
    assert chunk.add_name("x") == 0
    assert chunk.names == ["x", "y"]


def test_chunk_emit_returns_offset():
    chunk = Chunk()
    off0 = chunk.emit(Op.LOAD_NULL)
    off1 = chunk.emit(Op.POP)
    assert off0 == 0
    assert off1 == 1


# ─── Literals ────────────────────────────────────────────────────


def test_compile_number_literal_expr_stmt():
    chunk = _compile("5")
    assert chunk.constants == [5]
    assert chunk.code == [
        (Op.LOAD_CONST, 0),
        (Op.POP,),
        (Op.RETURN,),
    ]


def test_compile_string_literal_expr_stmt():
    chunk = _compile('"hi"')
    assert chunk.constants == ["hi"]
    assert chunk.code == [
        (Op.LOAD_CONST, 0),
        (Op.POP,),
        (Op.RETURN,),
    ]


def test_compile_bool_literal_uses_dedicated_opcodes():
    chunk = _compile("true")
    assert chunk.constants == []
    assert chunk.code == [(Op.LOAD_TRUE,), (Op.POP,), (Op.RETURN,)]


def test_compile_null_literal_uses_dedicated_opcode():
    chunk = _compile("null")
    assert chunk.constants == []
    assert chunk.code == [(Op.LOAD_NULL,), (Op.POP,), (Op.RETURN,)]


# ─── Assignment and let ──────────────────────────────────────────


def test_compile_assign_stores_via_name_pool():
    chunk = _compile("x = 42")
    assert chunk.constants == [42]
    assert chunk.names == ["x"]
    assert chunk.code == [
        (Op.LOAD_CONST, 0),
        (Op.STORE_NAME, 0),
        (Op.RETURN,),
    ]


def test_compile_let_emits_same_bytecode_as_assign_for_now():
    # The Let vs Assign distinction (fresh local vs chain-walking) will
    # diverge once STORE_LOCAL lands. For now the bytecode is identical.
    let_chunk = _compile("let y = 7")
    assign_chunk = _compile("y = 7")
    assert let_chunk.code == assign_chunk.code
    assert let_chunk.constants == assign_chunk.constants
    assert let_chunk.names == assign_chunk.names


# ─── Binary ops ──────────────────────────────────────────────────


def test_compile_binary_add():
    chunk = _compile("z = 1 + 2")
    assert chunk.constants == [1, 2]
    assert chunk.code == [
        (Op.LOAD_CONST, 0),
        (Op.LOAD_CONST, 1),
        (Op.ADD,),
        (Op.STORE_NAME, 0),
        (Op.RETURN,),
    ]


def test_compile_binary_sub_mul_div_mod():
    chunk = _compile("z = (4 - 1) * 2 / 6 % 5")
    # Don't pin the precise order — just that all the arithmetic
    # opcodes show up in the order their precedence dictates.
    ops = [instr[0] for instr in chunk.code]
    assert Op.SUB in ops
    assert Op.MUL in ops
    assert Op.DIV in ops
    assert Op.MOD in ops


def test_compile_unary_minus():
    chunk = _compile("x = -3")
    assert chunk.constants == [3]
    assert chunk.code == [
        (Op.LOAD_CONST, 0),
        (Op.NEG,),
        (Op.STORE_NAME, 0),
        (Op.RETURN,),
    ]


# ─── Identifier lookup ───────────────────────────────────────────


def test_compile_identifier_loads_by_name():
    chunk = _compile("x = 1\ny = x")
    assert chunk.names == ["x", "y"]
    # Body: store x, then load x, store y.
    assert chunk.code == [
        (Op.LOAD_CONST, 0),
        (Op.STORE_NAME, 0),
        (Op.LOAD_NAME, 0),
        (Op.STORE_NAME, 1),
        (Op.RETURN,),
    ]


# ─── NotImplementedError surface ─────────────────────────────────


def test_compile_unsupported_statement_raises_not_implemented():
    # `ClassDef` codegen isn't supported yet (lands later).
    with pytest.raises(NotImplementedError):
        _compile("class Foo { init() {} }")


# ─── Collections (v2.27.7) ───────────────────────────────────────


def test_compile_empty_list():
    chunk = _compile("xs = []")
    ops = [instr[0] for instr in chunk.code]
    assert ops == [Op.BUILD_LIST, Op.STORE_NAME, Op.RETURN]
    # BUILD_LIST with count 0.
    assert chunk.code[0] == (Op.BUILD_LIST, 0)


def test_compile_list_literal_pushes_then_builds():
    chunk = _compile("xs = [1 | 2 | 3]")
    assert chunk.constants == [1, 2, 3]
    # 3 LOAD_CONSTs in order, then BUILD_LIST 3.
    assert chunk.code == [
        (Op.LOAD_CONST, 0),
        (Op.LOAD_CONST, 1),
        (Op.LOAD_CONST, 2),
        (Op.BUILD_LIST, 3),
        (Op.STORE_NAME, 0),
        (Op.RETURN,),
    ]


def test_compile_dict_literal_alternates_key_value():
    chunk = _compile('d = {"a": 1 | "b": 2}')
    ops = [instr[0] for instr in chunk.code]
    # Each pair pushes key then value, BUILD_DICT with count.
    assert ops == [
        Op.LOAD_CONST,  # "a"
        Op.LOAD_CONST,  # 1
        Op.LOAD_CONST,  # "b"
        Op.LOAD_CONST,  # 2
        Op.BUILD_DICT,
        Op.STORE_NAME,
        Op.RETURN,
    ]
    assert chunk.code[4] == (Op.BUILD_DICT, 2)


def test_compile_index_expression():
    chunk = _compile("y = xs[0]")
    ops = [instr[0] for instr in chunk.code]
    assert ops == [
        Op.LOAD_NAME,
        Op.LOAD_CONST,
        Op.GET_INDEX,
        Op.STORE_NAME,
        Op.RETURN,
    ]


def test_compile_index_assign_emits_set_index():
    chunk = _compile("xs[0] = 99")
    ops = [instr[0] for instr in chunk.code]
    assert ops == [
        Op.LOAD_NAME,
        Op.LOAD_CONST,
        Op.LOAD_CONST,
        Op.SET_INDEX,
        Op.RETURN,
    ]


# ─── For loops (v2.27.8) ─────────────────────────────────────────


def test_compile_for_loop_emits_get_iter_iter_next_pop():
    chunk = _compile("for x in [1 | 2] { y = x }")
    ops = [instr[0] for instr in chunk.code]
    # iter expr (BUILD_LIST), GET_ITER, ITER_NEXT, STORE_NAME x,
    # body (LOAD_NAME x, STORE_NAME y), JUMP back, POP (cleanup),
    # RETURN.
    assert Op.GET_ITER in ops
    assert Op.ITER_NEXT in ops
    # ITER_NEXT's target should be the POP that cleans up the iter.
    iter_next_idx = next(
        i for i, instr in enumerate(chunk.code) if instr[0] == Op.ITER_NEXT
    )
    target = chunk.code[iter_next_idx][1]
    assert chunk.code[target][0] == Op.POP


def test_compile_for_break_jumps_to_pop_cleanup():
    chunk = _compile("for x in [1 | 2] { break }")
    # break emits a JUMP. Its target should be the POP that cleans
    # up the iter at end-of-loop.
    jumps = [
        (i, instr) for i, instr in enumerate(chunk.code) if instr[0] == Op.JUMP
    ]
    # The break's JUMP (target > current ip) vs the back-edge (target < ip).
    forward_jumps = [(i, j) for i, j in jumps if j[1] > i]
    assert len(forward_jumps) == 1
    break_target = forward_jumps[0][1][1]
    assert chunk.code[break_target][0] == Op.POP


# ─── Function definitions and calls (v2.27.9) ────────────────────


def test_compile_func_def_emits_load_const_store_name():
    from rot.codegen import RotFunctionValue
    chunk = _compile("funct foo() { return 1 }")
    # Outer chunk: LOAD_CONST (the RotFunctionValue), STORE_NAME foo,
    # RETURN.
    ops = [instr[0] for instr in chunk.code]
    assert ops == [Op.LOAD_CONST, Op.STORE_NAME, Op.RETURN]
    func = chunk.constants[0]
    assert isinstance(func, RotFunctionValue)
    assert func.name == "foo"
    assert func.params == []
    # The function's own chunk should contain LOAD_CONST 1 + RETURN_VALUE
    # (the user's `return 1`), plus the defensive fall-through
    # LOAD_NULL + RETURN_VALUE the compiler appends.
    inner_ops = [instr[0] for instr in func.chunk.code]
    assert inner_ops == [
        Op.LOAD_CONST,
        Op.RETURN_VALUE,
        Op.LOAD_NULL,
        Op.RETURN_VALUE,
    ]


def test_compile_call_pushes_function_then_args_then_emits_call():
    chunk = _compile("funct add(a | b) { return a + b }\nx = add(2 | 3)")
    # Find the CALL instruction. Just before it: the args (2 and 3)
    # were LOAD_CONSTed; before that, `add` was LOAD_NAMEd.
    call_idx = next(
        i for i, instr in enumerate(chunk.code) if instr[0] == Op.CALL
    )
    assert chunk.code[call_idx] == (Op.CALL, 2)
    assert chunk.code[call_idx - 1][0] == Op.LOAD_CONST
    assert chunk.code[call_idx - 2][0] == Op.LOAD_CONST
    assert chunk.code[call_idx - 3][0] == Op.LOAD_NAME


def test_compile_return_with_value_and_without():
    chunk = _compile("funct a() { return 7 }\nfunct b() { return }")
    a, b = chunk.constants[:2]
    # Function `a` body: LOAD_CONST 7, RETURN_VALUE, then fall-through.
    assert a.chunk.code[0] == (Op.LOAD_CONST, 0)
    assert a.chunk.code[1] == (Op.RETURN_VALUE,)
    # Function `b` body: LOAD_NULL, RETURN_VALUE, then fall-through.
    assert b.chunk.code[0] == (Op.LOAD_NULL,)
    assert b.chunk.code[1] == (Op.RETURN_VALUE,)


# ─── Comparison ops (v2.27.1) ────────────────────────────────────


def test_compile_eq_ne_lt_le_gt_ge():
    # Each operator becomes its own opcode after both sides are loaded.
    for src_op, expected in [
        ("==", Op.EQ),
        ("!=", Op.NE),
        ("<", Op.LT),
        ("<=", Op.LE),
        (">", Op.GT),
        (">=", Op.GE),
    ]:
        chunk = _compile(f"x = 1 {src_op} 2")
        assert chunk.code[2][0] == expected, (
            f"expected {expected.name} for {src_op!r}, got {chunk.code[2][0]}"
        )


def test_compile_not_unary():
    chunk = _compile("x = not true")
    assert chunk.code == [
        (Op.LOAD_TRUE,),
        (Op.NOT,),
        (Op.STORE_NAME, 0),
        (Op.RETURN,),
    ]


# ─── if / elseif / else (v2.27.2) ────────────────────────────────


def test_compile_if_without_else_emits_skip_jump():
    chunk = _compile("if (true) { x = 1 }")
    # Expected layout:
    #   LOAD_TRUE
    #   JUMP_IF_FALSE → past the body's JUMP
    #   LOAD_CONST 0 (1)
    #   STORE_NAME 0 (x)
    #   JUMP → end (past everything)
    #   RETURN
    ops = [instr[0] for instr in chunk.code]
    assert ops == [
        Op.LOAD_TRUE,
        Op.JUMP_IF_FALSE,
        Op.LOAD_CONST,
        Op.STORE_NAME,
        Op.JUMP,
        Op.RETURN,
    ]
    # The JUMP_IF_FALSE target should be the IP right after the
    # then-block's JUMP, i.e. index 5 (which is RETURN).
    assert chunk.code[1] == (Op.JUMP_IF_FALSE, 5)
    # The then-block's JUMP also lands at index 5.
    assert chunk.code[4] == (Op.JUMP, 5)


def test_compile_if_else_branches_to_separate_blocks():
    chunk = _compile("if (true) { x = 1 } else { x = 2 }")
    ops = [instr[0] for instr in chunk.code]
    # then-block + JUMP + else-block + RETURN.
    assert ops == [
        Op.LOAD_TRUE,
        Op.JUMP_IF_FALSE,
        Op.LOAD_CONST, Op.STORE_NAME, Op.JUMP,
        Op.LOAD_CONST, Op.STORE_NAME,
        Op.RETURN,
    ]
    # JUMP_IF_FALSE skips over the then-block and its JUMP (5 instrs
    # from start of if), so it should target index 5.
    assert chunk.code[1][1] == 5
    # The then-block's JUMP targets the end (index 7, the RETURN).
    assert chunk.code[4][1] == 7


def test_compile_if_with_elif_chain_emits_one_skip_per_branch():
    chunk = _compile(
        "if (1 == 1) { x = 1 }\n"
        "elseif (1 == 2) { x = 2 }\n"
        "else { x = 3 }\n"
    )
    # Count JUMP_IF_FALSE: one per condition (the if + one elif).
    ji_count = sum(1 for instr in chunk.code if instr[0] == Op.JUMP_IF_FALSE)
    assert ji_count == 2
    # Count JUMP: one per non-else branch (the if's and the elif's).
    j_count = sum(1 for instr in chunk.code if instr[0] == Op.JUMP)
    assert j_count == 2


# ─── while / break / continue (v2.27.3) ──────────────────────────


def test_compile_while_emits_back_edge():
    chunk = _compile("while (false) { x = 1 }")
    ops = [instr[0] for instr in chunk.code]
    # Expect: LOAD_FALSE, JUMP_IF_FALSE, body (LOAD_CONST, STORE_NAME),
    # JUMP back to start, RETURN.
    assert ops == [
        Op.LOAD_FALSE,
        Op.JUMP_IF_FALSE,
        Op.LOAD_CONST,
        Op.STORE_NAME,
        Op.JUMP,
        Op.RETURN,
    ]
    # The JUMP at index 4 should target index 0 (loop start).
    assert chunk.code[4] == (Op.JUMP, 0)
    # The JUMP_IF_FALSE at index 1 should target index 5 (past the
    # body's JUMP — the RETURN).
    assert chunk.code[1] == (Op.JUMP_IF_FALSE, 5)


def test_compile_break_emits_jump_to_loop_end():
    chunk = _compile("while (true) { break }")
    # The break compiles to a JUMP whose target is patched to the IP
    # right after the loop's back-edge JUMP.
    breaks = [
        (i, instr) for i, instr in enumerate(chunk.code) if instr[0] == Op.JUMP
    ]
    # Two JUMPs: the break (forward) and the back-edge (backward).
    assert len(breaks) == 2
    # Back-edge targets 0 (loop start).
    backedge = next(b for b in breaks if b[1][1] == 0)
    # The other is the break — its target should be past everything.
    break_jump = next(b for b in breaks if b[1][1] != 0)
    assert break_jump[1][1] > backedge[0]


def test_compile_continue_emits_jump_to_loop_start():
    chunk = _compile("while (true) { continue }")
    # continue → JUMP back to IP 0 (loop start).
    continue_jumps = [
        instr for instr in chunk.code
        if instr[0] == Op.JUMP and instr[1] == 0
    ]
    # The continue + the back-edge both jump to 0.
    assert len(continue_jumps) == 2


def test_compile_break_outside_loop_raises():
    with pytest.raises(InterpreterError):
        _compile("break")


def test_compile_continue_outside_loop_raises():
    with pytest.raises(InterpreterError):
        _compile("continue")


# ─── and / or short-circuit (v2.27.3) ────────────────────────────


def test_compile_and_uses_dup_and_jump_if_false():
    chunk = _compile("x = true and false")
    ops = [instr[0] for instr in chunk.code]
    # LOAD_TRUE, DUP, JUMP_IF_FALSE, POP, LOAD_FALSE, STORE_NAME, RETURN.
    assert ops == [
        Op.LOAD_TRUE,
        Op.DUP,
        Op.JUMP_IF_FALSE,
        Op.POP,
        Op.LOAD_FALSE,
        Op.STORE_NAME,
        Op.RETURN,
    ]


def test_compile_or_uses_dup_and_jump_if_true():
    chunk = _compile("x = true or false")
    ops = [instr[0] for instr in chunk.code]
    assert ops == [
        Op.LOAD_TRUE,
        Op.DUP,
        Op.JUMP_IF_TRUE,
        Op.POP,
        Op.LOAD_FALSE,
        Op.STORE_NAME,
        Op.RETURN,
    ]
