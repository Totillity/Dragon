from dragon.run import run_file, Path

from dragon.common import DragonError

DragonError.debug = True

run_file(Path("test.drgn"), delete_c=True)
