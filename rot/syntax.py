"""Recursive-descent parser: turns a Token stream into an AST.

Grammar (as of v1.8.0 — adds statements: funct, if/elseif/else, blocks):

    program     := stmt*
    stmt        := func_def | if_stmt | expr_stmt
    func_def    := 'funct' IDENT '(' params? ')' block
    params      := IDENT ('|' IDENT)*
    if_stmt     := 'if' '(' expr ')' block (elif_branch)* else_branch?
    elif_branch := 'elseif' '(' expr ')' block
    else_branch := 'else' block
    block       := '{' stmt* '}'
    expr_stmt   := expr
    expr        := binary
    binary      := atom_or_call (BIN_OP atom_or_call)*       # Pratt
    atom_or_call:= atom call_tail?
    call_tail   := '(' args ')'
    args        := ( expr ('|' expr)* )?
    atom        := callable | NUMBER | STRING_LIT | '(' expr ')'
    callable    := IDENT | 'cout' | 'coutln'

Whitespace, NEWLINE, and COMMENT tokens are stripped up front — the
parser doesn't care about source layout.

Operator precedence (higher binds tighter):

    5  *  /                                  factor
    4  +  -                                  term
    3  <  <=  >  >=                          comparison
    2  ==  !=                                equality
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

# Infix operator precedences for Pratt parsing. Higher = binds tighter.
_INFIX_PRECEDENCE: dict[str, int] = {
    "EQ_EQ": 2, "NEQ": 2,
    "LESSTHAN": 3, "LE": 3, "GREATERTHAN": 3, "GE": 3,
    "ADDITION": 4, "SUBTRACTION": 4,
    "MULTIPLICATION": 5, "DIVISION": 5,
}


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
        tok = self._peek()
        if tok is None:
            raise ParserError("unexpected end of input")
        if tok.kind == "FUNCTION":
            return self._parse_func_def()
        if tok.kind == "IF":
            return self._parse_if_stmt()
        return ast.ExprStmt(expr=self._parse_expression())

    def _parse_func_def(self) -> ast.FuncDef:
        self._consume("FUNCTION")
        name_tok = self._consume("IDENT")
        self._consume("L_PAREN")
        params: list[str] = []
        if not self._check("R_PAREN"):
            params.append(self._consume("IDENT").lexeme)
            while self._check("COMMA"):
                self._advance()
                params.append(self._consume("IDENT").lexeme)
        self._consume("R_PAREN")
        body = self._parse_block()
        return ast.FuncDef(name=name_tok.lexeme, params=params, body=body)

    def _parse_if_stmt(self) -> ast.IfStmt:
        self._consume("IF")
        self._consume("L_PAREN")
        cond = self._parse_expression()
        self._consume("R_PAREN")
        then_block = self._parse_block()

        elif_branches: list[ast.ElifBranch] = []
        while self._check("ELIF"):
            self._advance()
            self._consume("L_PAREN")
            elif_cond = self._parse_expression()
            self._consume("R_PAREN")
            elif_body = self._parse_block()
            elif_branches.append(ast.ElifBranch(cond=elif_cond, body=elif_body))

        else_block: ast.Block | None = None
        if self._check("ELSE"):
            self._advance()
            else_block = self._parse_block()

        return ast.IfStmt(
            cond=cond,
            then_block=then_block,
            elif_branches=elif_branches,
            else_block=else_block,
        )

    def _parse_block(self) -> ast.Block:
        self._consume("L_CURLY")
        statements: list[ast.Statement] = []
        while not self._check("R_CURLY"):
            if self._at_end():
                raise ParserError("unterminated block — expected '}'")
            statements.append(self._parse_statement())
        self._consume("R_CURLY")
        return ast.Block(statements=statements)

    def _parse_expression(self) -> ast.Expression:
        return self._parse_binary(0)

    def _parse_binary(self, min_prec: int) -> ast.Expression:
        left = self._parse_atom_or_call()
        while True:
            tok = self._peek()
            if tok is None:
                break
            prec = _INFIX_PRECEDENCE.get(tok.kind)
            if prec is None or prec < min_prec:
                break
            op_tok = self._advance()
            # `prec + 1` makes operators left-associative; use `prec`
            # for right-associative operators (none yet in rot).
            right = self._parse_binary(prec + 1)
            left = ast.BinaryOp(op=op_tok.lexeme, left=left, right=right)
        return left

    def _parse_atom_or_call(self) -> ast.Expression:
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

        if tok.kind == "L_PAREN":
            self._advance()
            expr = self._parse_expression()
            self._consume("R_PAREN")
            return expr
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
