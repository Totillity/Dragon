from typing import Tuple


class Token:
    def __init__(self, typ: str, text: str, line: int, pos: Tuple[int, int]):
        self.type = typ
        self.text = text
        self.line = line
        self.pos = pos

    def __eq__(self, other: 'Token'):
        return self.type == other.type and self.text == other.text

    def __repr__(self):
        return f"Token({self.type!r}, {self.text!r})"
