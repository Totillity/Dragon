import sys


class DragonError(Exception):
    def __init__(self, message, line, line_pos: (int, int)):
        self.message = message
        self.line = line
        self.line_pos = line_pos

    def finish(self, path: str, full_text: str):
        if full_text and self.line > 0:
            lines = full_text.split("\n")

            offender = lines[self.line-1]

            arrow_size = self.line_pos[1] - self.line_pos[0]
            left_over = (len(offender) - self.line_pos[1])

            arrows = " " * self.line_pos[0] + "^" * arrow_size + " " * left_over

            cut_len = len(offender) - len(offender.lstrip())
            arrows = arrows[cut_len:]

            offender = offender.lstrip()

            err_start = "    " + str(self.line) + " | "
            lines = [
                "File: " + path,
                err_start + offender,
                " "*len(err_start) + arrows,
                "Error: " + self.message
            ]
            msg = "\n".join(lines)
        else:
            msg = self.message

        sys.stderr.write(msg + "\n")
        sys.exit()
