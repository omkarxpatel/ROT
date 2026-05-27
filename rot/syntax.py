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
# Note: FSTRING must be present so `return f"..."` is recognized — its
# omission (P91) caused `return f"..."` to be parsed as a bare `return`
# followed by an orphan f-string expression statement.
_EXPR_STARTS = {
    "IDENT", "PRINT", "PRINTLN", "NUMBER", "STRING_LIT", "FSTRING",
    "TRUE", "FALSE", "NULL", "THIS",
    "L_PAREN", "L_BRACKET", "L_CURLY",
    "SUBTRACTION", "NOT",
}


_COMPOUND_ASSIGN_TOKENS: dict[str, str] = {
    "PLUS_EQ":    "+",
    "MINUS_EQ":   "-",
    "STAR_EQ":    "*",
    "SLASH_EQ":   "/",
    "PERCENT_EQ": "%",
}


# Friendly user-facing names for token kinds. The parser's internal
# `tok.kind` strings are jargon (`L_PAREN`, `COMMA`, `EQ_EQ`, ...) — fine
# for the lexer's table but unhelpful in user-facing error messages.
# ``_token_display`` looks up a friendly form; falls through to the raw
# kind for anything not covered. The COMMA entry is `'|'` because ROT
# uses `|` as the parameter/argument separator and lexes it under the
# `COMMA` kind for legacy reasons.
_TOKEN_DISPLAY: dict[str, str] = {
    # Punctuation & operators
    "L_PAREN":       "'('",
    "R_PAREN":       "')'",
    "L_CURLY":       "'{'",
    "R_CURLY":       "'}'",
    "L_BRACKET":     "'['",
    "R_BRACKET":     "']'",
    "COMMA":         "'|'",
    "DOT":           "'.'",
    "COLON":         "':'",
    "SETVALUE":      "'='",
    "EQ_EQ":         "'=='",
    "NEQ":           "'!='",
    "LESSTHAN":      "'<'",
    "LE":            "'<='",
    "GREATERTHAN":   "'>'",
    "GE":            "'>='",
    "ADDITION":      "'+'",
    "SUBTRACTION":   "'-'",
    "MULTIPLICATION": "'*'",
    "DIVISION":      "'/'",
    "MODULO":        "'%'",
    "PLUS_EQ":       "'+='",
    "MINUS_EQ":      "'-='",
    "STAR_EQ":       "'*='",
    "SLASH_EQ":      "'/='",
    "PERCENT_EQ":    "'%='",
    # Literals / structure
    "STRING_LIT":    "string literal",
    "FSTRING":       "f-string",
    "NUMBER":        "number",
    "IDENT":         "identifier",
    "NEWLINE":       "end of line",
    # Keywords
    "FUNCTION":      "'funct'",
    "RETURN":        "'return'",
    "IF":            "'if'",
    "ELIF":          "'elseif'",
    "ELSE":          "'else'",
    "WHILE":         "'while'",
    "FOR":           "'for'",
    "IN":            "'in'",
    "BREAK":         "'break'",
    "CONTINUE":      "'continue'",
    "CLASS":         "'class'",
    "THIS":          "'this'",
    "TRY":           "'try'",
    "CATCH":         "'catch'",
    "THROW":         "'throw'",
    "IMPORT":        "'import'",
    "LET":           "'let'",
    "TRUE":          "'true'",
    "FALSE":         "'false'",
    "NULL":          "'null'",
    "AND":           "'and'",
    "OR":            "'or'",
    "NOT":           "'not'",
    "PRINT":         "'cout'",
    "PRINTLN":       "'coutln'",
}


def _token_display(kind: str) -> str:
    """Map a token kind to its user-facing display string. Unknown kinds
    fall through unchanged — better to show the raw kind than to hide an
    error class behind a generic stand-in."""
    return _TOKEN_DISPLAY.get(kind, kind)


_ESCAPE_SEQUENCES: dict[str, str] = {
    "n":  "\n",
    "t":  "\t",
    "r":  "\r",
    "0":  "\0",
    '"':  '"',
    "'":  "'",
    "\\": "\\",
}


def _decode_string_escapes(raw: str) -> str:
    """Decode backslash escapes inside a string literal's content
    (with surrounding quotes already stripped)."""
    out: list[str] = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and i + 1 < len(raw):
            esc = raw[i + 1]
            out.append(_ESCAPE_SEQUENCES.get(esc, esc))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = [t for t in tokens if t.kind not in _SKIP_KINDS]
        self.pos = 0

    def parse(self) -> ast.Program:
        first_tok = self._peek()
        line = first_tok.line if first_tok else 1
        col = first_tok.col if first_tok else 1
        program = ast.Program(line=line, col=col)
        while not self._at_end():
            program.body.append(self._parse_statement())
        return program

    def _parse_statement(self) -> ast.Statement:
        tok = self._peek()
        if tok is None:
            eline, ecol = self._eof_pos()
            raise ParserError("unexpected end of input", eline, ecol)
        # Capture the line/col of the statement's first token; subdispatch
        # methods (`_parse_func_def` etc.) re-peek it themselves.
        sline, scol = tok.line, tok.col
        if tok.kind == "FUNCTION":
            return self._parse_func_def()
        if tok.kind == "IF":
            return self._parse_if_stmt()
        if tok.kind == "WHILE":
            return self._parse_while_stmt()
        if tok.kind == "FOR":
            return self._parse_for_stmt()
        if tok.kind == "RETURN":
            return self._parse_return()
        if tok.kind == "BREAK":
            self._advance()
            return ast.BreakStmt(line=sline, col=scol)
        if tok.kind == "CONTINUE":
            self._advance()
            return ast.ContinueStmt(line=sline, col=scol)
        if tok.kind == "CLASS":
            return self._parse_class_def()
        if tok.kind == "TRY":
            return self._parse_try_catch()
        if tok.kind == "THROW":
            return self._parse_throw()
        if tok.kind == "IMPORT":
            return self._parse_import()
        if tok.kind == "LET":
            return self._parse_let_stmt()
        # Otherwise: parse as expression, then check what follows.
        # `=` or compound (+=, -=, ...) → convert to assign/index-assign.
        expr = self._parse_expression()
        next_tok = self._peek()
        if next_tok is not None:
            if next_tok.kind == "SETVALUE":
                self._advance()
                return self._make_assign(expr, "=", self._parse_expression(), sline, scol)
            if next_tok.kind in _COMPOUND_ASSIGN_TOKENS:
                op = _COMPOUND_ASSIGN_TOKENS[next_tok.kind]
                self._advance()
                return self._make_assign(expr, op, self._parse_expression(), sline, scol)
        return ast.ExprStmt(expr=expr, line=sline, col=scol)

    def _make_assign(self, target: ast.Expression, op: str, value: ast.Expression,
                     sline: int = 0, scol: int = 0) -> ast.Statement:
        if isinstance(target, ast.Identifier):
            return ast.Assign(name=target.name, value=value, op=op, line=sline, col=scol)
        if isinstance(target, ast.Index):
            return ast.IndexAssign(
                target=target.target, index=target.index, value=value, op=op,
                line=sline, col=scol,
            )
        if isinstance(target, ast.MemberAccess):
            return ast.MemberAssign(
                target=target.target, member=target.member, value=value, op=op,
                line=sline, col=scol,
            )
        raise ParserError(
            f"invalid assignment target: {type(target).__name__}",
            sline, scol,
        )

    def _parse_while_stmt(self) -> ast.WhileStmt:
        while_tok = self._consume("WHILE")
        self._consume("L_PAREN")
        cond = self._parse_expression()
        self._consume("R_PAREN")
        body = self._parse_block()
        return ast.WhileStmt(cond=cond, body=body, line=while_tok.line, col=while_tok.col)

    def _parse_for_stmt(self) -> ast.ForStmt:
        for_tok = self._consume("FOR")
        var_tok = self._consume("IDENT")
        self._consume("IN")
        iter_expr = self._parse_expression()
        body = self._parse_block()
        return ast.ForStmt(var=var_tok.lexeme, iter=iter_expr, body=body,
                           line=for_tok.line, col=for_tok.col)

    def _parse_try_catch(self) -> ast.TryCatch:
        try_tok = self._consume("TRY")
        try_block = self._parse_block()
        self._consume("CATCH")
        self._consume("L_PAREN")
        catch_var = self._consume("IDENT").lexeme
        self._consume("R_PAREN")
        catch_block = self._parse_block()
        return ast.TryCatch(
            try_block=try_block, catch_var=catch_var, catch_block=catch_block,
            line=try_tok.line, col=try_tok.col,
        )

    def _parse_throw(self) -> ast.ThrowStmt:
        throw_tok = self._consume("THROW")
        value = self._parse_expression()
        return ast.ThrowStmt(value=value, line=throw_tok.line, col=throw_tok.col)

    def _parse_import(self) -> ast.ImportStmt:
        import_tok = self._consume("IMPORT")
        path_tok = self._consume("STRING_LIT")
        path = _decode_string_escapes(path_tok.lexeme[1:-1])
        return ast.ImportStmt(path=path, line=import_tok.line, col=import_tok.col)

    def _parse_let_stmt(self) -> ast.LetStmt:
        """`let IDENT = expr` — opt-in fresh-local binding.

        Reject `let obj.x = ...` and `let arr[0] = ...` — those don't make
        sense as fresh-local declarations. Likewise reject compound ops
        (`let x += 1`): `let` is for INTRODUCING a binding."""
        let_tok = self._consume("LET")
        name_tok = self._consume("IDENT")
        # Reject member/index/call tail after the name — only a bare IDENT
        # is a valid let target.
        next_tok = self._peek()
        if next_tok is not None and next_tok.kind in ("DOT", "L_BRACKET", "L_PAREN"):
            raise ParserError(
                f"`let` target must be a bare identifier, "
                f"got {_token_display(next_tok.kind)}",
                next_tok.line,
                next_tok.col,
            )
        if next_tok is not None and next_tok.kind != "SETVALUE":
            raise ParserError(
                f"expected '=' after `let {name_tok.lexeme}`, "
                f"got {_token_display(next_tok.kind)}",
                next_tok.line,
                next_tok.col,
            )
        if next_tok is None:
            raise ParserError(
                f"expected '=' after `let {name_tok.lexeme}`, got end of input",
                let_tok.line,
                let_tok.col,
            )
        self._consume("SETVALUE")
        value = self._parse_expression()
        return ast.LetStmt(name=name_tok.lexeme, value=value,
                           line=let_tok.line, col=let_tok.col)

    def _parse_class_def(self) -> ast.ClassDef:
        class_tok = self._consume("CLASS")
        name_tok = self._consume("IDENT")
        self._consume("L_CURLY")
        methods: list[ast.FuncDef] = []
        while not self._check("R_CURLY"):
            if self._at_end():
                eline, ecol = self._eof_pos()
                raise ParserError("unterminated class body", eline, ecol)
            method_tok = self._peek()
            method_name = self._consume("IDENT").lexeme
            self._consume("L_PAREN")
            params: list[str] = []
            if not self._check("R_PAREN"):
                params.append(self._consume("IDENT").lexeme)
                while self._check("COMMA"):
                    self._advance()
                    params.append(self._consume("IDENT").lexeme)
            self._consume("R_PAREN")
            body = self._parse_block()
            methods.append(ast.FuncDef(
                name=method_name, params=params, body=body,
                line=method_tok.line if method_tok else 0,
                col=method_tok.col if method_tok else 0,
            ))
        self._consume("R_CURLY")
        return ast.ClassDef(name=name_tok.lexeme, methods=methods,
                            line=class_tok.line, col=class_tok.col)

    def _parse_return(self) -> ast.Return:
        return_tok = self._consume("RETURN")
        tok = self._peek()
        if tok is not None and tok.kind in _EXPR_STARTS:
            return ast.Return(value=self._parse_expression(),
                              line=return_tok.line, col=return_tok.col)
        return ast.Return(value=None, line=return_tok.line, col=return_tok.col)

    def _parse_func_def(self) -> ast.FuncDef:
        func_tok = self._consume("FUNCTION")
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
        return ast.FuncDef(name=name_tok.lexeme, params=params, body=body,
                           line=func_tok.line, col=func_tok.col)

    def _parse_if_stmt(self) -> ast.IfStmt:
        if_tok = self._consume("IF")
        self._consume("L_PAREN")
        cond = self._parse_expression()
        self._consume("R_PAREN")
        then_block = self._parse_block()

        elif_branches: list[ast.ElifBranch] = []
        # P6: accept both the single keyword `elseif` and the two-word
        # form `else if`. The two-word form is detected by a peek-ahead
        # for IF following ELSE.
        while self._check("ELIF") or (
            self._check("ELSE")
            and self._peek(1) is not None
            and self._peek(1).kind == "IF"  # type: ignore[union-attr]
        ):
            if self._check("ELIF"):
                elif_tok = self._advance()
            else:
                # `else if` — consume ELSE, then use the IF token as the
                # branch's anchor so error messages point at the
                # condition's start.
                self._advance()  # ELSE
                elif_tok = self._advance()  # IF
            self._consume("L_PAREN")
            elif_cond = self._parse_expression()
            self._consume("R_PAREN")
            elif_body = self._parse_block()
            elif_branches.append(ast.ElifBranch(
                cond=elif_cond, body=elif_body,
                line=elif_tok.line, col=elif_tok.col,
            ))

        else_block: ast.Block | None = None
        if self._check("ELSE"):
            self._advance()
            else_block = self._parse_block()

        return ast.IfStmt(
            cond=cond,
            then_block=then_block,
            elif_branches=elif_branches,
            else_block=else_block,
            line=if_tok.line, col=if_tok.col,
        )

    def _parse_block(self) -> ast.Block:
        brace_tok = self._consume("L_CURLY")
        statements: list[ast.Statement] = []
        while not self._check("R_CURLY"):
            if self._at_end():
                # Report at the unclosed brace's position — that's where
                # the missing `}` belongs.
                raise ParserError(
                    "unterminated block — expected '}'",
                    brace_tok.line, brace_tok.col,
                )
            statements.append(self._parse_statement())
        self._consume("R_CURLY")
        return ast.Block(statements=statements,
                         line=brace_tok.line, col=brace_tok.col)

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
            left = ast.BinaryOp(op=op_tok.lexeme, left=left, right=right,
                                line=op_tok.line, col=op_tok.col)
        return left

    def _parse_prefix(self) -> ast.Expression:
        tok = self._peek()
        if tok is None:
            eline, ecol = self._eof_pos()
            raise ParserError("unexpected end of input", eline, ecol)
        if tok.kind == "NOT":
            not_tok = self._advance()
            # `not` binds looser than comparisons but tighter than `and`/`or`.
            # Consuming with min_prec=4 means inner expression can include
            # comparisons but not and/or — so `not a == b` parses as
            # `not (a == b)` (matches Python).
            operand = self._parse_binary(4)
            return ast.UnaryOp(op="not", operand=operand,
                               line=not_tok.line, col=not_tok.col)
        if tok.kind == "SUBTRACTION":
            minus_tok = self._advance()
            # Unary minus is the tightest-binding prefix. Recursive so
            # `--x` parses as `-(-x)`.
            operand = self._parse_prefix()
            return ast.UnaryOp(op="-", operand=operand,
                               line=minus_tok.line, col=minus_tok.col)
        return self._parse_atom_or_call()

    def _parse_atom_or_call(self) -> ast.Expression:
        atom = self._parse_atom()
        while True:
            if self._check("L_PAREN"):
                atom = self._parse_call_tail(atom)
            elif self._check("L_BRACKET"):
                atom = self._parse_index_tail(atom)
            elif self._check("DOT"):
                atom = self._parse_member_tail(atom)
            else:
                break
        return atom

    def _parse_member_tail(self, target: ast.Expression) -> ast.MemberAccess:
        dot_tok = self._consume("DOT")
        # Allow keyword tokens after `.` — `obj.class`, `obj.if`, etc. all
        # parse as member access with the keyword's lexeme as the name.
        name_tok = self._peek()
        if name_tok is None:
            raise ParserError("expected member name after `.`",
                              dot_tok.line, dot_tok.col)
        if name_tok.kind != "IDENT" and not name_tok.lexeme.isidentifier():
            raise ParserError(
                f"expected member name after `.`, "
                f"got {_token_display(name_tok.kind)}",
                name_tok.line, name_tok.col,
            )
        self._advance()
        # Use the target's source position when available so the member
        # access reports the start of the chain (e.g. `obj.x.y` → position
        # of `obj`); fall back to the dot if the target has no line.
        tline = getattr(target, 'line', 0) or dot_tok.line
        tcol = getattr(target, 'col', 0) or dot_tok.col
        return ast.MemberAccess(target=target, member=name_tok.lexeme,
                                line=tline, col=tcol)

    def _parse_dict_literal(self) -> ast.DictLit:
        brace_tok = self._consume("L_CURLY")
        pairs: list[tuple[ast.Expression, ast.Expression]] = []
        if not self._check("R_CURLY"):
            pairs.append(self._parse_dict_pair())
            while self._check("COMMA"):
                self._advance()
                pairs.append(self._parse_dict_pair())
        self._consume("R_CURLY")
        return ast.DictLit(pairs=pairs, line=brace_tok.line, col=brace_tok.col)

    def _parse_dict_pair(self) -> tuple[ast.Expression, ast.Expression]:
        key = self._parse_expression()
        self._consume("COLON")
        value = self._parse_expression()
        return (key, value)

    def _parse_call_tail(self, callee: ast.Expression) -> ast.Call:
        paren_tok = self._consume("L_PAREN")
        args: list[ast.Expression] = []
        if not self._check("R_PAREN"):
            args.append(self._parse_expression())
            while self._check("COMMA"):
                self._advance()
                args.append(self._parse_expression())
        self._consume("R_PAREN")
        # Use the callee's source position so `foo(x)` reports the position
        # of `foo` rather than the `(`; fall back to the paren otherwise.
        tline = getattr(callee, 'line', 0) or paren_tok.line
        tcol = getattr(callee, 'col', 0) or paren_tok.col
        return ast.Call(callee=callee, args=args, line=tline, col=tcol)

    def _parse_index_tail(self, target: ast.Expression) -> ast.Index:
        bracket_tok = self._consume("L_BRACKET")
        index = self._parse_expression()
        self._consume("R_BRACKET")
        tline = getattr(target, 'line', 0) or bracket_tok.line
        tcol = getattr(target, 'col', 0) or bracket_tok.col
        return ast.Index(target=target, index=index, line=tline, col=tcol)

    def _parse_list_literal(self) -> ast.ListLit:
        bracket_tok = self._consume("L_BRACKET")
        elements: list[ast.Expression] = []
        if not self._check("R_BRACKET"):
            elements.append(self._parse_expression())
            while self._check("COMMA"):
                self._advance()
                elements.append(self._parse_expression())
        self._consume("R_BRACKET")
        return ast.ListLit(elements=elements,
                           line=bracket_tok.line, col=bracket_tok.col)

    def _parse_atom(self) -> ast.Expression:
        tok = self._peek()
        if tok is None:
            eline, ecol = self._eof_pos()
            raise ParserError("unexpected end of input", eline, ecol)

        if tok.kind == "THIS":
            self._advance()
            return ast.Identifier(name="this", line=tok.line, col=tok.col)
        if tok.kind == "L_PAREN":
            self._advance()
            expr = self._parse_expression()
            self._consume("R_PAREN")
            return expr
        if tok.kind == "L_BRACKET":
            return self._parse_list_literal()
        if tok.kind == "L_CURLY":
            return self._parse_dict_literal()
        if tok.kind in _NAME_LIKE:
            self._advance()
            return ast.Identifier(name=tok.lexeme, line=tok.line, col=tok.col)
        if tok.kind == "NUMBER":
            self._advance()
            return ast.NumberLit(
                value=float(tok.lexeme) if "." in tok.lexeme else int(tok.lexeme),
                line=tok.line, col=tok.col,
            )
        if tok.kind == "STRING_LIT":
            self._advance()
            # Strip surrounding quotes, then decode `\n`, `\t`, `\"`, etc.
            return ast.StringLit(value=_decode_string_escapes(tok.lexeme[1:-1]),
                                 line=tok.line, col=tok.col)
        if tok.kind == "FSTRING":
            self._advance()
            return self._parse_fstring_content(tok.lexeme[1:-1], tok.line, tok.col)
        if tok.kind == "TRUE":
            self._advance()
            return ast.BoolLit(value=True, line=tok.line, col=tok.col)
        if tok.kind == "FALSE":
            self._advance()
            return ast.BoolLit(value=False, line=tok.line, col=tok.col)
        if tok.kind == "NULL":
            self._advance()
            return ast.NullLit(line=tok.line, col=tok.col)
        raise ParserError(
            f"expected expression, got {_token_display(tok.kind)} "
            f"({tok.lexeme!r})",
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

    def _eof_pos(self) -> tuple[int, int]:
        """Return a (line, col) approximation for the end-of-input position:
        one column past the end of the last consumed token, on the same line.
        Falls back to (0, 0) when the token list is empty entirely."""
        # Prefer the most recent token in the stream (the last one parsed
        # or any token in the buffer) so the position is anchored to real
        # source. self.pos may have been advanced past the buffer; clamp.
        if not self.tokens:
            return (0, 0)
        idx = self.pos - 1 if self.pos > 0 else 0
        if idx >= len(self.tokens):
            idx = len(self.tokens) - 1
        tok = self.tokens[idx]
        return (tok.line, tok.col + max(1, len(tok.lexeme)))

    def _parse_fstring_content(self, content: str, line: int, col: int) -> ast.Expression:
        """Split f-string content into static text and `{expr}` interpolations,
        then desugar to a chain of `+` operations (with `str(...)` wrapping the
        expressions). No new AST node — uses existing StringLit / Call / BinaryOp.
        """
        from .lexer import Lexer  # local import to avoid load-time cycle

        parts: list[tuple[str, "object"]] = []
        i = 0
        while i < len(content):
            next_brace = content.find("{", i)
            if next_brace == -1:
                if i < len(content):
                    parts.append(("static", content[i:]))
                break
            if next_brace > i:
                parts.append(("static", content[i:next_brace]))
            end_brace = content.find("}", next_brace + 1)
            if end_brace == -1:
                raise ParserError("unterminated `{` in f-string", line, col)
            expr_text = content[next_brace + 1 : end_brace].strip()
            if not expr_text:
                raise ParserError("empty `{}` in f-string", line, col)
            inner_tokens = Lexer().tokenize(expr_text)
            inner_parser = Parser(inner_tokens)
            expr = inner_parser._parse_expression()
            # Inner parser must consume every token — otherwise the f-string
            # has garbage like `{1 2}` and we'd silently drop it.
            if not inner_parser._at_end():
                leftover = inner_parser._peek()
                raise ParserError(
                    f"unexpected token {leftover.lexeme!r} in f-string expression",
                    line, col,
                )
            parts.append(("expr", expr))
            i = end_brace + 1

        # Decode escapes in static segments.
        decoded: list[tuple[str, "object"]] = []
        for kind, value in parts:
            if kind == "static":
                decoded.append((kind, _decode_string_escapes(value)))  # type: ignore[arg-type]
            else:
                decoded.append((kind, value))

        if not decoded:
            return ast.StringLit(value="", line=line, col=col)

        result: ast.Expression | None = None
        for kind, value in decoded:
            if kind == "static":
                node: ast.Expression = ast.StringLit(value=value, line=line, col=col)  # type: ignore[arg-type]
            else:
                node = ast.Call(
                    callee=ast.Identifier(name="str", line=line, col=col),
                    args=[value],  # type: ignore[list-item]
                    line=line, col=col,
                )
            result = node if result is None else ast.BinaryOp(
                op="+", left=result, right=node, line=line, col=col,
            )
        assert result is not None
        return result

    def _consume(self, kind: str) -> Token:
        if self._check(kind):
            return self._advance()
        tok = self._peek()
        want = _token_display(kind)
        if tok is None:
            eline, ecol = self._eof_pos()
            raise ParserError(f"expected {want}, got end of input", eline, ecol)
        got = _token_display(tok.kind)
        raise ParserError(
            f"expected {want}, got {got}",
            tok.line,
            tok.col,
        )
