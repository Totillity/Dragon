from typing import Tuple


class Token:
    def __init__(self, typ: str, text: str, line: int, pos: Tuple[int, int]):
        self.type = typ
        self.text = text
        self.line = line
        self.pos = pos