from typing import List

import re

from dragon.common import DragonError, Token

ORDER = "START"


class ScanningError(DragonError):
    pass


basic_tokens = sorted([
    "=",
    "+=", "-=", "*=", "**=", "/=", "//=", "%=",
    "+", "-", "*", "**", "/", "//", "%",
    "<", ">", "<=", ">=", "==", "!=",
    "!", "~",

    '->',
    "(", ")", "[", "]", "{", "}", ".", ",", ";", ":"
], key=len, reverse=True)

keywords = [
    "var",
    "def", "class",
    "method", "attr",
    "if", "else",
    "while",
    "return",
    "and", "or", "as", "new"
]


letters = "abcdefghijklmnopqrstuvwxyz"
letters += letters.upper()

digits = "0123456789"


v = 3


class ExtendedString(str):
    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except IndexError:
            return "\0"


def scan(text: str) -> List[Token]:
    tokens = []
    pos = 0
    line = 1
    line_pos = 0

    text = ExtendedString(text)

    def advance(num):
        nonlocal pos, line_pos
        pos += num
        line_pos += num

    def advance_line():
        nonlocal pos, line, line_pos
        pos += 1
        line += 1
        line_pos = 0

    def add_if_match(s):
        if text[pos:].startswith(s):
            tokens.append(Token(s, s, line, (line_pos, line_pos + len(s))))
            advance(len(s))
            return True
        else:
            return False

    def add_regex(pattern, name):
        match_ = re.match(pattern, text[pos:]).group()
        tokens.append(Token(name, match_, line, (line_pos, line_pos + len(match_))))
        advance(len(match_))

    while pos < len(text):
        if any(add_if_match(basic_token) for basic_token in basic_tokens):
            pass
        else:   # Not a basic token
            # start = line_pos
            if text[pos:pos+1] == "0x":
                add_regex("0x[A-Fa-f0-9]+", "hex")
            elif text[pos] in digits:
                add_regex(r"[0-9]+(?:\.[0-9]+)?", "num")
            elif text[pos] == "\"":
                add_regex(r'"(?:\\.|[^"\\])*"', "str")
            elif text[pos] in letters:
                match = re.match("[_a-zA-Z][_a-zA-Z0-9]*", text[pos:]).group()
                if match in keywords:
                    tokens.append(Token(match, match, line, (line_pos, line_pos + len(match))))
                else:
                    tokens.append(Token("ident", match, line, (line_pos, line_pos + len(match))))
                advance(len(match))
            elif text[pos] == " ":
                advance(1)
            elif text[pos] == "\n":
                advance_line()
            elif text[pos] == "#":     # '#' used for special directives
                advance(1)
                hashcode = text[pos:].split(" ", 1)[0]
                if hashcode == "":       # '# ' is a comment
                    while text[pos] != "\n":
                        advance(1)
                    advance_line()
                else:
                    raise ScanningError(f"Unknown hashcode: {hashcode}", line, (line_pos, line_pos + len(hashcode)))
            else:
                raise ScanningError(f"Cannot scan tokens from {text[pos]}", line, (line_pos, line_pos+1))

    return tokens
