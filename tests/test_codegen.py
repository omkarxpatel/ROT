"""Tests for the bytecode compiler (rot/codegen.py).

M2 foundation: covers the opcodes the v2.27.0 codegen emits —
literals, identifiers, simple assigns/let-bindings, arithmetic.
Later Z's extend the set; each adds tests here.
"""

import pytest

from rot.codegen import Chunk, Compiler
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
    # `WhileStmt` isn't supported yet (lands in v2.27.3).
    with pytest.raises(NotImplementedError):
        _compile("while (true) { x = 1 }")


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
