"""Orchestrates the lex -> parse -> execute pipeline.

Three public methods so callers can mix and match: `compile()` returns the
generated Python source, `save()` writes it to disk, `execute()` runs it.
The pipeline is silent unless `trace=True` is passed to the constructor.
"""

from __future__ import annotations

import time

from colorama import Fore, init as colorama_init

from .emitter import Emitter
from .lexer import Lexer
from .syntax import Parser


class Compiler:
    def __init__(self, trace: bool = False) -> None:
        self.trace = trace
        if trace:
            colorama_init(autoreset=True)

    def compile(self, source: str) -> str:
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
            print(f"\n\n{Fore.RED}Process 3 - Emitter (AST -> Python):")

        started = time.time()
        python_code = Emitter().emit(program)

        if self.trace:
            print(f"Execution time: {round(time.time() - started, 7)}s")

        return python_code

    @staticmethod
    def save(python_code: str, output_file: str = "output.py") -> None:
        with open(output_file, "w") as py_file:
            py_file.write(python_code)

    def execute(self, python_code: str) -> None:
        if self.trace:
            print(f"\n\n{Fore.RED}Process 3 - Execution (output):\n")
        started = time.time()
        exec(python_code)
        if self.trace:
            print(f"\nExecution Time: {round(time.time() - started, 7)}s")
