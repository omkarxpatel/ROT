"""Orchestrates the lex -> parse -> interpret pipeline.

v2.0.0 replaced the Python-source emitter + exec() flow with a direct
tree-walking interpreter (rot/interpreter.py). ROT no longer compiles
to Python — it runs its own AST.

The emitter (rot/emitter.py) still exists for anyone who wants to
inspect an equivalent Python rendering, but it's no longer on the
default execution path.
"""

from __future__ import annotations

import time

from colorama import Fore, init as colorama_init

from . import ast
from .errors import ParserError, InterpreterError
from .interpreter import Interpreter
from .lexer import Lexer
from .syntax import Parser


class Compiler:
    def __init__(self, trace: bool = False) -> None:
        self.trace = trace
        if trace:
            colorama_init(autoreset=True)

    def parse(self, source: str) -> ast.Program:
        if self.trace:
            print(f"{Fore.RED}Input File:\n\n{Fore.RESET}{source}\n\n")
            print(f"{Fore.RED}Process 1 - Tokenizer:")

        started = time.time()
        tokens = Lexer(trace=self.trace).tokenize(source)

        if self.trace:
            print(f"\nExecution time: {round(time.time() - started, 7)}s")
            print(f"Tokens: {len(tokens)}")
            print(f"\n\n{Fore.RED}Process 2 - Parser (AST):")

        started = time.time()
        try:
            program = Parser(tokens).parse()
        except RecursionError:
            raise ParserError("expression too deeply nested")

        if self.trace:
            print(f"AST: Program(body=[{len(program.body)} statements])")
            print(f"Execution time: {round(time.time() - started, 7)}s")

        return program

    def run(self, source: str, source_path: "str | None" = None) -> None:
        program = self.parse(source)
        if self.trace:
            print(f"\n\n{Fore.RED}Process 3 - Interpreter (output):\n")
        started = time.time()
        interp = Interpreter()
        if source_path is not None:
            import os
            interp.set_source_dir(os.path.dirname(os.path.abspath(source_path)))
        try:
            interp.execute(program)
        except RecursionError:
            # Last-resort safety net — most rot recursion is caught in
            # _evaluate_call, but a few interpreter sites (e.g. nested
            # _evaluate of deep expressions) can still trip the Python
            # recursion limit. Either way: don't let a Python traceback
            # escape.
            raise InterpreterError("call stack too deep")
        if self.trace:
            print(f"\nExecution time: {round(time.time() - started, 7)}s")
