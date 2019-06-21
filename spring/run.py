import os
from pathlib import Path

from spring.passes import compile_drgn, parse, scan
from spring.common import SpringError

__all__ = ['run_file', 'compile_file',
           'Path']


class CompilingError(SpringError):
    pass


def compile_file(path: Path, compiler='clang', delete_c=True):
    with path.open("r") as file:
        contents = file.read()

    try:
        unit = compile_drgn(parse(scan(contents)), path)
    except SpringError as e:
        e.finish('<string>', contents)
        raise

    for program in unit.programs:
        with program.path.with_suffix(".h").open("w") as header:
            with program.path.with_suffix(".c").open("w") as source:
                base_name = program.path.with_suffix('').name.replace("__", "")
                program.generate(base_name, header, source)

    c_files = Path(os.path.realpath(__file__)).parent / "std_files"
    dragon_c = str(c_files / "dragon.c")
    list_c = str(c_files / "list.c")

    result = os.system(f"{compiler} -O3 -o {path.with_suffix('')} "
                       f"{' '.join(str(program.path.with_suffix('.c')) for program in unit.programs)} "
                       f"{dragon_c} {list_c} "
                       f"-Wno-parentheses-equality")

    if result != 0:
        CompilingError("Error during compiling generated C code", 0, (0, 0)).finish(str(path), "")

    if delete_c:
        for program in unit.programs:
            program.path.with_suffix(".c").unlink()
            program.path.with_suffix(".h").unlink()


def run_file(path: Path, compiler='clang', delete_c=True, delete_exe=True):
    with path.open("r") as file:
        contents = file.read()

    try:
        unit = compile_drgn(parse(scan(contents)), path)
    except SpringError as e:
        e.finish('<string>', contents)
        raise

    for program in unit.programs:
        with program.path.with_suffix(".h").open("w") as header:
            with program.path.with_suffix(".c").open("w") as source:
                base_name = program.path.with_suffix('').name.replace("__", "")
                program.generate(base_name, header, source)

    c_files = Path(os.path.realpath(__file__)).parent / "std_files"
    dragon_c = str(c_files / "dragon.c")
    list_c = str(c_files / "list.c")

    result = os.system(f"{compiler} -O3 -o {path.with_suffix('')} "
                       f"{' '.join(str(program.path.with_suffix('.c')) for program in unit.programs)} "
                       f"{dragon_c} {list_c} "
                       f"-Wno-parentheses-equality")

    if result != 0:
        CompilingError("Error during compiling generated C code", 0, (0, 0)).finish(str(path), "")

    os.system(f"./{path.with_suffix('')}")

    if delete_c:
        for program in unit.programs:
            program.path.with_suffix(".c").unlink()
            program.path.with_suffix(".h").unlink()

    if delete_exe:
        path.with_suffix("").unlink()
