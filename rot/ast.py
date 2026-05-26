"""Abstract syntax tree node types for the .rot language.

v1's "parser" was a token-to-string translator with no tree. v2 builds
a real AST: the recursive-descent parser in rot/syntax.py produces
these nodes; future phases (semantic analysis, tree-walking
interpreter, bytecode, codegen) consume them.

Phase 1 scope is intentionally narrow — expression statements with
function calls, identifiers, and literals. FuncDef / IfStmt / BinaryOp
arrive in later phases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass
class Identifier:
    name: str


@dataclass
class NumberLit:
    value: int


@dataclass
class StringLit:
    value: str


@dataclass
class Call:
    callee: "Expression"
    args: list["Expression"] = field(default_factory=list)


@dataclass
class BinaryOp:
    op: str
    left: "Expression"
    right: "Expression"


Expression = Union[Identifier, NumberLit, StringLit, Call, BinaryOp]


@dataclass
class ExprStmt:
    expr: Expression


@dataclass
class Block:
    statements: list["Statement"] = field(default_factory=list)


@dataclass
class FuncDef:
    name: str
    params: list[str]
    body: Block


@dataclass
class ElifBranch:
    cond: Expression
    body: Block


@dataclass
class IfStmt:
    cond: Expression
    then_block: Block
    elif_branches: list[ElifBranch] = field(default_factory=list)
    else_block: "Block | None" = None


@dataclass
class Assign:
    name: str
    value: Expression


@dataclass
class Return:
    value: "Expression | None" = None


Statement = Union[ExprStmt, FuncDef, IfStmt, Assign, Return]


@dataclass
class Program:
    body: list[Statement] = field(default_factory=list)
