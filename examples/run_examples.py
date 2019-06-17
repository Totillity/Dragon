from dragon.run import run_file, Path

from dragon.common import DragonError

# If you want developer (of Dragon) errors, set debug to True. It will show the python traceback
DragonError.debug = False

programs = [
    'main_function',
    'hello_world',
    'fibonacci',
    'macros',
    'arrays'
]

for program in programs:
    run_file(Path(program + ".drgn"))
