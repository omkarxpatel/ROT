"""Recursive-descent parser: turns a Token stream into an AST.

Phase 1 grammar (intentionally narrow):

    program     := stmt*
    stmt        := expr_stmt
    expr_stmt   := expr
    expr        := call | atom
    call        := callable '(' args ')'
    args        := ( expr ('|' expr)* )?
    callable    := IDENT | 'cout' | 'coutln'
    atom        := callable | NUMBER | STRING_LIT

Whitespace, NEWLINE, and COMMENT tokens are stripped up front — Phase
1 doesn't care about source layout.
"""

from __future__ import annotations

from . import ast
from .errors import ParserError
from .token import Token


_SKIP_KINDS = {"SPACE", "NEWLINE", "COMMENT"}

# Kinds the parser is willing to treat as a name in atom position.
# PRINT and PRINTLN (cout / coutln) are keyword-classified by the lexer
# but should still be callable like ordinary identifiers.
_NAME_LIKE = {"IDENT", "PRINT", "PRINTLN"}


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = [t for t in tokens if t.kind not in _SKIP_KINDS]
        self.pos = 0

    def parse(self) -> ast.Program:
        program = ast.Program()
        while not self._at_end():
            program.body.append(self._parse_statement())
        return program

    def _parse_statement(self) -> ast.Statement:
        return ast.ExprStmt(expr=self._parse_expression())

    def _parse_expression(self) -> ast.Expression:
        atom = self._parse_atom()
        if self._check("L_PAREN"):
            return self._parse_call_tail(atom)
        return atom

    def _parse_call_tail(self, callee: ast.Expression) -> ast.Call:
        self._consume("L_PAREN")
        args: list[ast.Expression] = []
        if not self._check("R_PAREN"):
            args.append(self._parse_expression())
            while self._check("COMMA"):
                self._advance()
                args.append(self._parse_expression())
        self._consume("R_PAREN")
        return ast.Call(callee=callee, args=args)

    def _parse_atom(self) -> ast.Expression:
        tok = self._peek()
        if tok is None:
            raise ParserError("unexpected end of input")

        if tok.kind in _NAME_LIKE:
            self._advance()
            return ast.Identifier(name=tok.lexeme)
        if tok.kind == "NUMBER":
            self._advance()
            return ast.NumberLit(value=int(tok.lexeme))
        if tok.kind == "STRING_LIT":
            self._advance()
            return ast.StringLit(value=tok.lexeme[1:-1])
        raise ParserError(
            f"expected expression, got {tok.kind} ({tok.lexeme!r})",
            tok.line,
            tok.col,
        )

    def _peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    def _check(self, kind: str) -> bool:
        tok = self._peek()
        return tok is not None and tok.kind == kind

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _consume(self, kind: str) -> Token:
        if self._check(kind):
            return self._advance()
        tok = self._peek()
        if tok is None:
            raise ParserError(f"expected {kind}, got end of input")
        raise ParserError(
            f"expected {kind}, got {tok.kind}",
            tok.line,
            tok.col,
        )
