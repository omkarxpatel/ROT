"""Keyword and token tables shared by the lexer and parser."""

DOUBLE_CHECKING = {
    "/": "//",
}

LOOKUP_KEYWORD = {
    # reserved words
    "cout": "PRINT",
    "coutln": "PRINTLN",
    "funct": "FUNCTION",
    "elseif": "ELSEIF",
    "if": r"\if",
    "else": r"\else",

    # quotes
    '"': r'\"',
    "'": r"\'",

    # arithmetic operators
    "+": r"\+",
    "-": r"\-",
    "*": r"\*",
    "/": r"\/",
    "<": r"\<",
    ">": r"\>",

    # special symbols
    "(": r"\(",
    ")": r"\)",
    " ": r"\s+",
    "\n": r"\n",
    "=": r"\=",
    "//": r"//",
    "|": r"\|",
    "{": r"\{",
}

KEYWORD_TYPES = {
    # reserved words
    r"\d+": "NUMBER",
    r"[a-z]+": "STRING",
    r"[A-Z]+": "STRING",
    "print": "PRINT",
    "funct ": "FUNCTION",
    r"\if": "IF",
    r"\else": "ELSE",
    r"\elseif": "ELIF",

    # quotes
    r'\"': "QUOTE",
    r'\'': "SINGLE_QUOTE",

    # arithmetic operators
    r"\+": "ADDITION",
    r"\-": "SUBTRACTION",
    r"\*": "MULTIPLICATION",
    r"\/": "DIVISION",
    r"\=": "SETVALUE",
    r"\<": "LESSTHAN",
    r"\>": "GREATERTHAN",

    # special symbols
    r"\(": "L_PAREN",
    r"\)": "R_PAREN",
    r"\s+": "SPACE",
    r"\n": "NEWLINE",
    r"//": "COMMENT",
    r"\|": "COMMA",
    r"\{": "L_CURLY",
}

ANTI_KEYWORD = {
    "PRINT": "print",
    "PRINTLN": "print*",
    "COMMENT": "# ",
    "COMMA": ",",
    "FUNCTION": "def",
    "L_CURLY": ":",
    "ELSEIF": "elif",
}

SYNTAX_TREE = {
    "PRINT": 'cout("_")',
    "FUNCTION": "funct",
}


def _expand_lookups() -> None:
    keyword_config = {
        "0123456789": r"\d+",
        "abcdefghijklmnopqrstuvwxyz": r"[a-z]+",
    }
    for characters, regex in keyword_config.items():
        for character in characters:
            LOOKUP_KEYWORD[character] = regex

    for character in "+-*/":
        LOOKUP_KEYWORD[character] = rf"\{character}"


_expand_lookups()
