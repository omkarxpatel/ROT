"""Abstract syntax tree node types for the .rot language.

v1's "parser" was a token-to-string translator with no tree. v2 builds
a real AST: the recursive-descent parser in rot/syntax.py produces
these nodes; future phases (semantic analysis, tree-walking
interpreter, bytecode, codegen) consume them.

Phase 1 scope is intentionally narrow — expression statements with
function calls, identifiers, and literals. FuncDef / IfStmt / BinaryOp
arrive in later phases.

Source locations:
Every node carries optional ``line`` and ``col`` source-position fields
(default 0 = unknown). The parser populates them from the first token of
the corresponding source span. The interpreter threads them into
``InterpreterError`` raises so runtime errors carry source location.
Source-position fields live AFTER any existing fields with defaults so
positional construction (kwargs in syntax.py) keeps working.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass
class Identifier:
    name: str
    line: int = 0
    col: int = 0


@dataclass
class NumberLit:
    value: "int | float"
    line: int = 0
    col: int = 0


@dataclass
class StringLit:
    value: str
    line: int = 0
    col: int = 0


@dataclass
class BoolLit:
    value: bool
    line: int = 0
    col: int = 0


@dataclass
class NullLit:
    line: int = 0
    col: int = 0


@dataclass
class Call:
    callee: "Expression"
    args: list["Expression"] = field(default_factory=list)
    line: int = 0
    col: int = 0


@dataclass
class BinaryOp:
    op: str
    left: "Expression"
    right: "Expression"
    line: int = 0
    col: int = 0


@dataclass
class UnaryOp:
    op: str
    operand: "Expression"
    line: int = 0
    col: int = 0


@dataclass
class ListLit:
    elements: list["Expression"] = field(default_factory=list)
    line: int = 0
    col: int = 0


@dataclass
class Index:
    target: "Expression"
    index: "Expression"
    line: int = 0
    col: int = 0


@dataclass
class MemberAccess:
    target: "Expression"
    member: str
    line: int = 0
    col: int = 0


@dataclass
class DictLit:
    pairs: list[tuple["Expression", "Expression"]] = field(default_factory=list)
    line: int = 0
    col: int = 0


Expression = Union[
    Identifier, NumberLit, StringLit, BoolLit, NullLit, Call, BinaryOp, UnaryOp,
    ListLit, Index, MemberAccess, DictLit,
]


@dataclass
class ExprStmt:
    expr: Expression
    line: int = 0
    col: int = 0


@dataclass
class Block:
    statements: list["Statement"] = field(default_factory=list)
    line: int = 0
    col: int = 0


@dataclass
class FuncDef:
    name: str
    params: list[str]
    body: Block
    line: int = 0
    col: int = 0


@dataclass
class ElifBranch:
    cond: Expression
    body: Block
    line: int = 0
    col: int = 0


@dataclass
class IfStmt:
    cond: Expression
    then_block: Block
    elif_branches: list[ElifBranch] = field(default_factory=list)
    else_block: "Block | None" = None
    line: int = 0
    col: int = 0


@dataclass
class Assign:
    name: str
    value: Expression
    # `=` for plain assignment, `+`/`-`/`*`/`/`/`%` for compound assign.
    op: str = "="
    line: int = 0
    col: int = 0


@dataclass
class LetStmt:
    """`let name = expr` — an explicit fresh-local binding. Unlike `Assign`,
    a `LetStmt` never chain-walks: it always binds in the current scope.
    Use to shadow an outer name in a nested scope (the v2.10.0
    closure-mutation feature would otherwise silently mutate the outer)."""
    name: str
    value: Expression
    line: int = 0
    col: int = 0


@dataclass
class Return:
    value: "Expression | None" = None
    line: int = 0
    col: int = 0


@dataclass
class WhileStmt:
    cond: Expression
    body: Block
    line: int = 0
    col: int = 0


@dataclass
class ForStmt:
    var: str
    iter: Expression
    body: Block
    line: int = 0
    col: int = 0


@dataclass
class IndexAssign:
    target: Expression
    index: Expression
    value: Expression
    op: str = "="
    line: int = 0
    col: int = 0


@dataclass
class MemberAssign:
    target: Expression
    member: str
    value: Expression
    op: str = "="
    line: int = 0
    col: int = 0


@dataclass
class BreakStmt:
    line: int = 0
    col: int = 0


@dataclass
class ContinueStmt:
    line: int = 0
    col: int = 0


@dataclass
class ClassDef:
    name: str
    methods: list[FuncDef] = field(default_factory=list)
    line: int = 0
    col: int = 0


@dataclass
class TryCatch:
    try_block: Block
    catch_var: str
    catch_block: Block
    line: int = 0
    col: int = 0


@dataclass
class ThrowStmt:
    value: Expression
    line: int = 0
    col: int = 0


@dataclass
class ImportStmt:
    path: str
    line: int = 0
    col: int = 0


Statement = Union[
    ExprStmt, FuncDef, IfStmt, Assign, LetStmt, Return, WhileStmt,
    ForStmt, IndexAssign, MemberAssign, BreakStmt, ContinueStmt,
    ClassDef, TryCatch, ThrowStmt, ImportStmt,
]


@dataclass
class Program:
    body: list[Statement] = field(default_factory=list)
    line: int = 0
    col: int = 0
