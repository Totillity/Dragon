from dataclasses import dataclass, field
from typing import List

import re

from spring.common import SpringError, Token

ORDER = "START"


class ScanningError(SpringError):
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

macro_basic_tokens = sorted([
    "$(", "${",
    ")$", "}$",
    "=>",
], key=len, reverse=True)


keywords = [
    "var", "del",
    "def", "class",
    "method", "attr",
    "if", "else",
    "while",
    "return",
    "and", "or", "as", "new"
]


letters = "abcdefghijklmnopqrstuvwxyz"
letters += letters.upper()
letters += "_"

digits = "0123456789"


v = 3


class ExtendedString(str):
    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except IndexError:
            return "\0"


@dataclass()
class State:
    pos: int = field(default=0)
    line: int = field(default=1)
    line_pos: int = field(default=0)


def scan(text: str) -> List[Token]:
    tokens = []
    state = State()

    macro_mode = False

    text = ExtendedString(text)

    def advance(num):
        state.pos += num
        state.line_pos += num

    def advance_line():
        state.pos += 1
        state.line += 1
        state.line_pos = 0

    def expect(s):
        if text[state.pos:state.pos + len(s)] == s:
            advance(len(s))
        else:
            raise ScanningError(f"Expected {s!r}, got {text[state.pos:state.pos + len(s)]!r}", state.line,
                                (state.line_pos, state.line_pos + len(s)))

    def next_is(s):
        if text[state.pos:state.pos + len(s)] == s:
            return True
        else:
            return False

    def add_if_match(s):
        if text[state.pos:state.pos + len(s)] == s:
            # print(s, True)
            tokens.append(Token(s, s, state.line, (state.line_pos, state.line_pos + len(s))))
            advance(len(s))
            return True
        else:
            # print(s, False)
            return False

    def add_regex(pattern, name):
        match_ = re.match(pattern, text[state.pos:]).group()
        tokens.append(Token(name, match_, state.line, (state.line_pos, state.line_pos + len(match_))))
        advance(len(match_))

    while state.pos < len(text):
        if macro_mode and any(add_if_match(basic_token) for basic_token in macro_basic_tokens):
            pass
        elif any(add_if_match(basic_token) for basic_token in basic_tokens):
            pass
        else:   # Not a basic token
            # start = line_pos
            if text[state.pos:state.pos + 2] == "0x":
                add_regex("0x[A-Fa-f0-9]+", "hex")
            elif text[state.pos] in digits:
                add_regex(r"[0-9]+(?:\.[0-9]+)?", "num")
            elif text[state.pos] == "\"":
                add_regex(r'"(?:\\.|[^"\\])*"', "str")
            elif text[state.pos] in letters:
                match = re.match("[_a-zA-Z][_a-zA-Z0-9]*", text[state.pos:]).group()
                if match in keywords:
                    tokens.append(Token(match, match, state.line, (state.line_pos, state.line_pos + len(match))))
                else:
                    tokens.append(Token("ident", match, state.line, (state.line_pos, state.line_pos + len(match))))
                advance(len(match))
            elif text[state.pos] == " ":
                advance(1)
            elif text[state.pos] == "\n":
                advance_line()
            elif text[state.pos] == "#":  # '#' used for special directives
                hashcode = text[state.pos:].split(None, 1)[0][1:]
                advance(1)
                if hashcode == "":       # '# ' is a comment
                    while text[state.pos] != "\n":
                        advance(1)
                    advance_line()
                elif hashcode == "macro":
                    macro_mode = True
                    tokens.append(Token("macro", "macro", state.line, (state.line_pos, state.line_pos + len("macro"))))
                    expect("macro")
                elif hashcode == "endmacro":
                    macro_mode = False
                    tokens.append(
                        Token("endmacro", "endmacro", state.line, (state.line_pos, state.line_pos + len("endmacro"))))
                    expect("endmacro")
                elif hashcode == "import":
                    tokens.append(
                        Token("import", "import", state.line, (state.line_pos, state.line_pos + len("import"))))
                    advance(len("import"))
                else:
                    raise ScanningError(f"Unknown hashcode: {hashcode}", state.line,
                                        (state.line_pos, state.line_pos + len(hashcode)))
            elif macro_mode and text[state.pos] == "$" and text[state.pos + 1] in letters:
                start = state.line_pos
                match = re.match(r"\$[_a-zA-Z][_a-zA-Z0-9]*", text[state.pos:]).group()
                advance(len(match))
                tokens.append(Token("$ident", match, state.line, (start, state.line_pos)))
            else:
                raise ScanningError(f"Cannot scan tokens from {text[state.pos]}", state.line,
                                    (state.line_pos, state.line_pos + 1))

    return tokens
