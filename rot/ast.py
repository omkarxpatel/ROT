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


Statement = Union[ExprStmt]


@dataclass
class Program:
    body: list[Statement] = field(default_factory=list)
