import pathlib

from dragon.run import run_file
import argparse


def main():
    parser = argparse.ArgumentParser(prog="dragon")
    parser.add_argument("file", help="The .drgn file to compile")
    parser.add_argument("--run", action="store_true", help="Run the resulting executable")
    parser.add_argument("--show_c", action="store_true", help="Do not delete the .c and .h files")
    parser.add_argument("--compiler", default="clang", help="Set the compiler (defaults to clang)")

    args = parser.parse_args()

    place = pathlib.Path(args.file)

    run_file(place)


if __name__ == "__main__":
    main()
