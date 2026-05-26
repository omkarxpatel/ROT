"""Tokenizer: turns .rot source text into a flat list of tokens."""

import re

from .keywords import LOOKUP_KEYWORD, KEYWORD_TYPES


class Lexer:
    def __init__(self) -> None:
        self.position = 0
        self.tokens: list[list[str]] = []

    def tokenize(self, source: str) -> list[list[str]]:
        print("-" * 30)
        operations = 0

        while self.position < len(source):
            current = source[self.position]

            try:
                identifier = LOOKUP_KEYWORD[current]
                regex = re.compile(identifier)
                token = regex.match(source, self.position)

                if not identifier:
                    print("Invalid Identifier at position: ", self.position)

                try:
                    token_type = KEYWORD_TYPES[identifier]
                    if token_type == "STRING":
                        try:
                            token_type = LOOKUP_KEYWORD[token.group(0)] or "STRING"
                        except Exception:
                            pass
                except Exception:
                    token_type = "UNKNOWN"

                self.position = token.end()
                self.tokens.append([token.group(0), token_type])

                spaces = " " * (5 - len(str(operations)))
                spaces2 = " " * (10 - len(str(repr(token.group(0)))))
                print(f"{operations}{spaces}|  {repr(token.group(0))}{spaces2}|  {token_type}")

            except Exception:
                self.position += 1

            operations += 1

        print("-" * 30)
        return self.tokens
