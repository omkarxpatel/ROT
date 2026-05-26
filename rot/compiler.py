"""Orchestrates the lex → parse → execute pipeline."""

import os
import time

from colorama import Fore, init as colorama_init

from .lexer import Lexer
from .parser import Parser


class Compiler:
    def __init__(self) -> None:
        colorama_init(autoreset=True)

    @staticmethod
    def save(python_code: str, output_file: str = "output.py") -> None:
        with open(output_file, "w") as py_file:
            py_file.write(python_code)
        print(f"Saved to {output_file}")

    def run(self, source: str) -> None:
        os.system("clear")
        overall = time.time()
        print(f"{Fore.RED}Input File:\n\n{Fore.RESET}{source}\n\n")

        # Process 1 — tokenize
        print(f"{Fore.RED}Process 1 - Tokenizer:")
        started = time.time()
        tokens = Lexer().tokenize(source)
        print(f"\nExecution time: {round(time.time() - started, 7)}s\nOperations: {len(tokens)}")

        # Process 2 — parse to Python
        print(f"\n\n{Fore.RED}Process 2 - Parser:")
        started = time.time()
        python_code = Parser().parse(tokens)
        self.save(python_code)
        print(f"\nExecution time: {round(time.time() - started, 7)}s")

        # Process 3 — execute
        print(f"\n\n{Fore.RED}Process 3 - Execution (output):\n")
        exec(python_code)
        print(f"\nExecution Time: {round(time.time() - overall, 7)}s")
