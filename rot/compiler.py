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
        program = Parser(tokens).parse()

        if self.trace:
            print(f"AST: Program(body=[{len(program.body)} statements])")
            print(f"Execution time: {round(time.time() - started, 7)}s")

        return program

    def run(self, source: str) -> None:
        program = self.parse(source)
        if self.trace:
            print(f"\n\n{Fore.RED}Process 3 - Interpreter (output):\n")
        started = time.time()
        Interpreter().execute(program)
        if self.trace:
            print(f"\nExecution time: {round(time.time() - started, 7)}s")
