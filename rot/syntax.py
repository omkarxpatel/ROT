"""Recursive-descent parser: turns a Token stream into an AST.

Grammar (as of v2.2.0 — adds while, unary ops, booleans, logical ops):

    program     := stmt*
    stmt        := func_def | if_stmt | while_stmt | return_stmt | assign | expr_stmt
    func_def    := 'funct' IDENT '(' params? ')' block
    params      := IDENT ('|' IDENT)*
    if_stmt     := 'if' '(' expr ')' block (elif_branch)* else_branch?
    elif_branch := 'elseif' '(' expr ')' block
    else_branch := 'else' block
    while_stmt  := 'while' '(' expr ')' block
    return_stmt := 'return' expr?
    assign      := IDENT '=' expr                       # lookahead disambiguates from expr_stmt
    block       := '{' stmt* '}'
    expr_stmt   := expr
    expr        := binary
    binary      := prefix (BIN_OP prefix)*              # Pratt
    prefix      := ('not' prefix) | ('-' prefix) | atom_or_call
    atom_or_call:= atom call_tail?
    call_tail   := '(' args ')'
    args        := ( expr ('|' expr)* )?
    atom        := callable | NUMBER | STRING_LIT | 'true' | 'false' | 'null' | '(' expr ')'
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
    "OR": 1,
    "AND": 2,
    # Reserved: prefix `not` sits between AND and equality (precedence 3).
    "EQ_EQ": 4, "NEQ": 4,
    "LESSTHAN": 5, "LE": 5, "GREATERTHAN": 5, "GE": 5,
    "ADDITION": 6, "SUBTRACTION": 6,
    "MULTIPLICATION": 7, "DIVISION": 7, "MODULO": 7,
}


# Token kinds that can start an expression (used to detect bare `return`).
_EXPR_STARTS = {
    "IDENT", "PRINT", "PRINTLN", "NUMBER", "STRING_LIT",
    "TRUE", "FALSE", "NULL", "L_PAREN", "SUBTRACTION", "NOT",
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
        if tok.kind == "WHILE":
            return self._parse_while_stmt()
        if tok.kind == "RETURN":
            return self._parse_return()
        # Assignment: IDENT '=' expr — one-token lookahead distinguishes
        # from a bare-identifier expression statement.
        if tok.kind == "IDENT":
            after = self._peek(1)
            if after is not None and after.kind == "SETVALUE":
                return self._parse_assign()
        return ast.ExprStmt(expr=self._parse_expression())

    def _parse_while_stmt(self) -> ast.WhileStmt:
        self._consume("WHILE")
        self._consume("L_PAREN")
        cond = self._parse_expression()
        self._consume("R_PAREN")
        body = self._parse_block()
        return ast.WhileStmt(cond=cond, body=body)

    def _parse_assign(self) -> ast.Assign:
        name_tok = self._consume("IDENT")
        self._consume("SETVALUE")
        value = self._parse_expression()
        return ast.Assign(name=name_tok.lexeme, value=value)

    def _parse_return(self) -> ast.Return:
        self._consume("RETURN")
        tok = self._peek()
        if tok is not None and tok.kind in _EXPR_STARTS:
            return ast.Return(value=self._parse_expression())
        return ast.Return(value=None)

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
        left = self._parse_prefix()
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

    def _parse_prefix(self) -> ast.Expression:
        tok = self._peek()
        if tok is None:
            raise ParserError("unexpected end of input")
        if tok.kind == "NOT":
            self._advance()
            # `not` binds looser than comparisons but tighter than `and`/`or`.
            # Consuming with min_prec=4 means inner expression can include
            # comparisons but not and/or — so `not a == b` parses as
            # `not (a == b)` (matches Python).
            operand = self._parse_binary(4)
            return ast.UnaryOp(op="not", operand=operand)
        if tok.kind == "SUBTRACTION":
            self._advance()
            # Unary minus is the tightest-binding prefix. Recursive so
            # `--x` parses as `-(-x)`.
            operand = self._parse_prefix()
            return ast.UnaryOp(op="-", operand=operand)
        return self._parse_atom_or_call()

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
        if tok.kind == "TRUE":
            self._advance()
            return ast.BoolLit(value=True)
        if tok.kind == "FALSE":
            self._advance()
            return ast.BoolLit(value=False)
        if tok.kind == "NULL":
            self._advance()
            return ast.NullLit()
        raise ParserError(
            f"expected expression, got {tok.kind} ({tok.lexeme!r})",
            tok.line,
            tok.col,
        )

    def _peek(self, offset: int = 0) -> Token | None:
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else None

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
