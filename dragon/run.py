import os
from pathlib import Path
import sys

from dragon.passes import compile_drgn, parse, scan
from dragon.common import DragonError, cgen as ast

__all__ = ['program_from_str', 'program_from_file',
           'run_str', 'run_file',
           'generate_program', 'compile_program',
           'run_program',
           'Path']


class CompilingError(DragonError):
    pass


def program_from_str(text: str) -> ast.Program:
    try:
        program = compile_drgn(parse(scan(text)))
    except DragonError as e:
        e.finish('<string>', text)
        raise
    return program


def program_from_file(file: Path) -> ast.Program:
    try:
        with file.open("r") as dragon_file:
            text = dragon_file.read()
    except FileNotFoundError:
        print(f"File {file} does not exist", file=sys.stderr)
        sys.exit()

    return program_from_str(text)


def run_str(text: str, file_name: Path = None, compiler='clang'):
    program = program_from_str(text)

    if file_name is None:
        file_name = Path("__run_str__")

    run_program(program, file_name, compiler)


def run_file(file: Path, compiler='clang', delete_c=True, delete_exe=True):
    program = program_from_file(file)

    to_delete = []
    if delete_c:
        to_delete += ['.h', '.c']
    if delete_exe:
        to_delete += ['']

    run_program(program, file, compiler, to_delete)


def generate_program(program: ast.Program, file_name: Path):
    with file_name.with_suffix(".h").open("w") as header:
        with file_name.with_suffix(".c").open("w") as source:
            base_name = file_name.with_suffix('').name.replace("__", "")
            program.generate(base_name, header, source)


def compile_program(program: ast.Program, file_name: Path, compiler='clang'):
    generate_program(program, file_name)
    c_files = Path(os.path.realpath(__file__)).parent / "c_files"
    dragon_c = str(c_files / "dragon.c")
    list_c = str(c_files / "list.c")

    result = os.system(f"{compiler} -O3 -I/Users/MagilanS/PycharmProjects/Dragon2 -o {file_name.with_suffix('')} "
                       f"{file_name.with_suffix('.c')} {dragon_c} {list_c}")
    if result != 0:
        CompilingError("Error during compiling generated C code", 0, (0, 0)).finish(str(file_name), "")


def run_program(program: ast.Program, file_name: Path, compiler='clang', delete=('', '.h', '.c')):
    compile_program(program, file_name, compiler)

    os.system(f"./{file_name.with_suffix('')}")

    delete_files(file_name, delete)


def delete_files(file_name: Path, delete=('', '.h', '.c')):
    for suffix in delete:
        file_name.with_suffix(suffix).unlink()
