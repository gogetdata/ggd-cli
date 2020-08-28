# -------------------------------------------------------------------------------------------------------------
## Import Statements
# -------------------------------------------------------------------------------------------------------------
from __future__ import print_function

import json
import os
import re
import sys

GGD_INFO = "share/ggd_info"
METADATA = "channeldata.json"

# -------------------------------------------------------------------------------------------------------------
## Argument Parser
# -------------------------------------------------------------------------------------------------------------
def add_list_installed_packages(p):

    import argparse

    c = p.add_parser(
        "list",
        help="List the ggd data package(s) that are currently installed in a specific conda environment",
        description="Get a list of ggd data packages installed in the current or specified conda prefix/environment.",
    )
    c.add_argument(
        "-p",
        "--pattern",
        help="(Optional) pattern to match the name of the ggd data package.",
    )
    c.add_argument(
        "--prefix",
        default=None,
        help="(Optional) The name or the full directory path to a conda environment where a ggd recipe is stored. (Only needed if listing data files not in the current environment)",
    )
    c.add_argument("--reset", action="store_true", help=argparse.SUPPRESS)
    c.set_defaults(func=list_installed_packages)


# -------------------------------------------------------------------------------------------------------------
## Functions/Methods
# -------------------------------------------------------------------------------------------------------------


def load_json(jfile):
    """Method to load a json file into a dictionary

    load_json
    =========
    Method to load a json file 

    Parameters:
    ---------
    1) jfile: The path to the json file

    Returns:
    1) A dictionary of a json object 
    """

    with open(jfile) as jsonFile:
        return json.load(jsonFile)


def get_environment_variables(prefix):
    """Method to get ggd data package environment variables in a user specified conda environment/prefix

    get_environment_variables
    =========================
    Method to get the environment variables for each installed data package in a specific conda environment

    Parameters:
    -----------
    1) prefix: The conda environment/prefix to get environment variables for 

    Returns:
    ++++++++
    1) A dictionary with each key == env_var, and values == the path the environment variable is for
    """

    env_var_path = os.path.join(prefix, "etc", "conda", "activate.d", "env_vars.sh")
    env_vars = {}
    try:
        with open(env_var_path, "r") as env_file:
            for var in env_file:
                var_array = var.strip().split()
                if len(var_array) >= 2:
                    var_item_array = var_array[1].split("=")
                if len(var_item_array) >= 1:
                    env_vars[var_item_array[0]] = var_item_array[1]
    except (IOError, ValueError):
        return None

    ## Key = env_var, value = path
    return env_vars


def list_pkg_info(pkg_names, pkgs_dict, env_vars, conda_list, prefix, prefix_set=False):
    """Method to identify and display available data packages in a specific conda environment

    list_pkg_info
    =============
    Method to display the ggd data packages installed in a specific conda environment. If the 
     prefix is not set, the packages in the current environment will be displayed. If the --pattern
     flag is set, the package names will be filtered prior to this method.

    Parameters:
    -----------
    1) pkg_names: A list of package names to show. (List comes from ggd_info metadata file)
    2) pks_dict: The ggd_info metadata file as a dictionary (To get version and channel info)
    3) env_vars: A dictionary of environment variables. (Key = env_var name, value = path to file/dir)
    4) conda_list: A dictionary representing conda list output (from utils.get_conda_package_list())
    5) prefix: The prefix/conda environment to display information for. 
    6) prefix_set: True or False, whether the user set a prefix or not.
    """

    ## Create a 2d list for string formatting
    formatted_list = [
        ["    Name", "Pkg-Version", "Pkg-Build", "Channel", "Environment-Variables"]
    ]

    missing_in_conda = False
    missing_message = " [WARNING: Present in GGD but missing from Conda]"
    ## Iterate over each package in pkg_names
    for pkg in pkg_names:

        version = pkgs_dict[pkg]["version"]

        ## If package is present in both ggd metadata and conda metadata
        if pkg in conda_list:
            assert version == conda_list[pkg]["version"]
            build = conda_list[pkg]["build"]
            channel = "ggd-" + pkgs_dict[pkg]["tags"]["ggd-channel"]
            assert channel == conda_list[pkg]["channel"]

        ## If package is missing from conda metadata
        else:
            missing_in_conda = True
            build = missing_message
            channel = ""

        ## Get env_vars
        env_variables = []
        if (
            "ggd_" + pkg.replace("-", "_").replace(".", "_") + "_dir"
        ) in env_vars.keys():
            env_variables.append(
                " $ggd_" + pkg.replace("-", "_").replace(".", "_") + "_dir"
            )
        if (
            "ggd_" + pkg.replace("-", "_").replace(".", "_") + "_file"
        ) in env_vars.keys():
            env_variables.append(
                " $ggd_" + pkg.replace("-", "_").replace(".", "_") + "_file"
            )

        formatted_list.append([pkg, version, build, channel, ",".join(env_variables)])

    ## Print data pkg list
    print("\n\n# Packages in environment: {p}\n#".format(p=prefix))

    dash = "-" * 120
    for i in range(len(formatted_list)):
        if i == 0:
            print(dash)
            print(
                "{:<40s}{:>5s}{:>10s}{:>10s}{:>30s}".format(
                    formatted_list[i][0],
                    formatted_list[i][1],
                    formatted_list[i][2],
                    formatted_list[i][3],
                    formatted_list[i][4],
                )
            )
            print(dash)
        else:
            print(
                "-> {:<40s}{:>5s}{:>10s}{:>15s}{:^60s}\n".format(
                    formatted_list[i][0],
                    formatted_list[i][1],
                    formatted_list[i][2],
                    formatted_list[i][3],
                    formatted_list[i][4],
                )
            )

    ## Print environment variables info
    if prefix_set:
        print(
            "# The environment variables are only available when you are using the '{p}' conda environment.".format(
                p=prefix
            )
        )
    else:
        print("# To use the environment variables run `source activate base`")
        print(
            "# You can see the available ggd data package environment variables by running `ggd show-env`\n"
        )

    ## Print message if a package is missing from conda metadata
    if missing_in_conda:
        print(
            (
                "#\n# NOTE: Packages with the '{}' messages represent packages where the ggd"
                " packages is installed, but the package metadata has been removed from conda storage. This happens when"
                " the packages is uninstalled using conda rather then ggd. The package is still available for use and is"
                " in the same state as before the 'conda uninstall'. To fix the problem on conda's side, uninstall"
                " the package with 'ggd uninstall' and re-install with 'ggd install'.\n"
            ).format(missing_message)
        )


def list_installed_packages(parser, args):
    """Main method of `ggd list` used to list installed ggd data package in user specified conda environment/prefix

    list_installed_packages
    =======================
    Main method of ggd list. This method will check and set the conda environment/prefix, check the ggd info metdata file
     get environment variables for ggd data packages in the user specified conda prefix, get the installed data packages 
     from conda info, filter results based on user specified pattern, and provide the information to the display function.
    """

    from .utils import (
        conda_root,
        get_conda_package_list,
        get_conda_prefix_path,
        prefix_in_conda,
        update_installed_pkg_metadata,
    )

    ## Check prefix
    CONDA_ROOT = (
        get_conda_prefix_path(args.prefix)
        if args.prefix != None and prefix_in_conda(args.prefix)
        else conda_root()
    )

    ## If reset list
    if args.reset:
        print(
            "\n:ggd:list: The --reset flag was set. RESETTING ggd installed list metadata."
        )
        update_installed_pkg_metadata(args.prefix)
        print(
            "\n:ggd:list: Run 'ggd list' without --reset to see a list of installed ggd data packages"
        )
        print("\nDONE\n")
        sys.exit(0)

    ggd_info_path = os.path.join(CONDA_ROOT, GGD_INFO)

    ## Check that the ggd info dir exists. If not, create it
    if not os.path.isdir(ggd_info_path):
        update_installed_pkg_metadata(prefix=CONDA_ROOT)

    ## Load json metadata data as dictionary
    metadata = load_json(os.path.join(CONDA_ROOT, GGD_INFO, METADATA))

    ## Get the environment variables
    env_vars = get_environment_variables(CONDA_ROOT)

    ## Get conda package list
    ggd_packages = get_conda_package_list(CONDA_ROOT)

    ## Get final package list
    final_package_list = metadata["packages"].keys()

    ## Check if there is a user defined pattern
    pat = args.pattern if args.pattern != None else None
    if pat != None:
        matches = list(
            map(
                str,
                [
                    re.search(".*" + pat.lower() + ".*", x).group()
                    for x in metadata["packages"].keys()
                    if re.search(pat.lower(), x) != None
                ],
            )
        )
        if len(matches) < 1:
            # print("\n-> '{p}' did not match any installed data packages".format(p=args.pattern))
            sys.exit(
                "\n:ggd:list: '{p}' did not match any installed data packages".format(
                    p=args.pattern
                )
            )
            # sys.exit(0)
        else:
            final_package_list = matches

    ## Provide the results to stdout
    list_pkg_info(
        final_package_list,
        metadata["packages"],
        env_vars,
        ggd_packages,
        CONDA_ROOT,
        prefix_set=False if args.prefix == None else True,
    )
