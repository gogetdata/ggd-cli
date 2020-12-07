import argparse
import sys

from .__init__ import __version__
from .check_recipe import add_check_recipe
from .install import add_install
from .list_files import add_list_files
from .list_installed_pkgs import add_list_installed_packages
from .list_pkg_info import add_pkg_info
from .make_bash import add_make_bash
from .make_meta_recipe import add_make_metarecipe
from .predict_path import add_predict_path
from .search import add_search
from .show_env import add_show_env
from .uninstall import add_uninstall

if sys.version_info[0] < 3:
    print(
        "\n:ggd:WARNING: Python 2 is no longer maintained by python developers."
        " GGD will not maintain support for python 2 past December 31, 2020."
        " Python 2 may still work, but continued maintenance and support will"
        " be focused on python >=  3\n"
    )


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="ggd", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Installed version",
        action="version",
        version="%(prog)s " + str(__version__),
    )
    sub = parser.add_subparsers(title="[sub-commands]", dest="command")
    sub.required = True

    add_search(sub)

    add_predict_path(sub)

    add_install(sub)

    add_uninstall(sub)

    add_list_installed_packages(sub)

    add_list_files(sub)

    add_pkg_info(sub)

    add_show_env(sub)

    add_make_bash(sub)

    add_make_metarecipe(sub)

    add_check_recipe(sub)

    args = parser.parse_args(args)
    args.func(parser, args)


if __name__ == "__main__":
    sys.exit(main() or 0)
