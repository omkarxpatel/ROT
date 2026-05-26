"""Parser: turns a token stream into a Python source string."""

from .keywords import ANTI_KEYWORD, KEYWORD_TYPES, DOUBLE_CHECKING


class Parser:
    def parse(self, tokens: list[list[str]]) -> str:
        operations = 0
        idx = 0
        result = ""

        print("-" * 30)
        for value, token_type in tokens:
            parsed_value = ANTI_KEYWORD.get(token_type) or value

            if len(parsed_value) != 1:
                if parsed_value == "print":  # checks for newline at end
                    open_parens = 0
                    for i in range(idx, len(tokens)):
                        token = tokens[i][-1]
                        if token == "L_PAREN":
                            open_parens += 1
                        elif token == "R_PAREN":
                            open_parens -= 1
                            if open_parens == 0:
                                tokens.insert(i, [', end=""', "ENDL"])
                                idx = i + 2
                                break
                elif parsed_value == "print*":
                    parsed_value = parsed_value.strip("*")

            if parsed_value == "print":
                try:
                    if result[-5:] != "print":
                        result += parsed_value
                except Exception:
                    pass
            else:
                checker = DOUBLE_CHECKING.get(parsed_value) or None
                if checker:
                    next_token = tokens[operations + 1][0]
                    if next_token + parsed_value == checker:
                        result += ANTI_KEYWORD.get(KEYWORD_TYPES.get(checker))
                    else:
                        result += checker
                else:
                    result += parsed_value

            operations += 1

            if parsed_value == "\n" or token_type == "SPACE":
                value, parsed_value = repr(value), repr(parsed_value)

            spaces = " " * (5 - len(str(operations)))
            spaces2 = " " * (10 - len(value))
            print(f"{operations}{spaces}|  {value}{spaces2}->    {parsed_value}")

        print("-" * 30)
        return result
