"""Command-line entry point: `python -m rot <file.rot>`."""

import sys

from . import __version__
from .compiler import Compiler


def main() -> None:
    if len(sys.argv) != 2:
        print(f"rot {__version__}")
        print("Usage: python -m rot <filename.rot>")
        sys.exit(1)

    filename = sys.argv[1]
    if not filename.endswith(".rot"):
        print(f"File {filename} needs to be a .rot file")
        sys.exit(1)

    try:
        with open(filename, "r") as file:
            source = file.read()
    except FileNotFoundError:
        print(f"File '{filename}' not found.")
        sys.exit(1)

    Compiler().run(source)
