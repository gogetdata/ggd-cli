import sys
import argparse
from .__init__ import __version__
from . make_bash import add_make_bash
from . check_recipe import add_check_recipe
from . list_files import add_list_files
from . search import add_search
from . show_env import add_show_env

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(prog='ggd', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--version", help="Installed version",
                        action="version",
                        version="%(prog)s " + str(__version__))
    sub = parser.add_subparsers(title='[sub-commands]', dest='command')
    sub.required = True
    add_make_bash(sub)

    add_check_recipe(sub)

    add_list_files(sub)

    add_search(sub)
    
    add_show_env(sub)

    args = parser.parse_args(args)
    args.func(parser, args)








if __name__ == "__main__":
    sys.exit(main() or 0)

