import sys
import argparse
from .__init__ import __version__
from . make_bash import add_make_bash

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(prog='ggd', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--version", help="Installed version",
                        action="version",
                        version="%(prog)s " + str(__version__))
    sub = parser.add_subparsers(title='[sub-commands]', dest='command')

    add_make_bash(sub)

    args = parser.parse_args()
    args.func(parser, args)


if __name__ == "__main__":
    sys.exit(main() or 0)
