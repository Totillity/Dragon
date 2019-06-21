from spring.run import run_file, Path

from spring.common import SpringError

# If you want developer (of Dragon) errors, set debug to True. It will show the python traceback
SpringError.debug = False

programs = [
    'main_function',
    'hello_world',
    'fibonacci',
    'macros',
    'arrays',
    'imports',
    'on_delete',
    'classes',
    'strings',
    'overloading',
    'gc_test',
]

for program in programs:
    run_file(Path(program + ".drgn"), delete_c=True)
