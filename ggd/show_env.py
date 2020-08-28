from __future__ import print_function

import os
import re

from .utils import get_conda_env


def add_show_env(p):
    c = p.add_parser(
        "show-env",
        help="Show ggd data package environment variables available for the current conda environment",
        description="Display the environment variables for data packages installed in the current conda environment",
    )
    c.add_argument(
        "-p",
        "--pattern",
        help="regular expression pattern to match the name of the variable desired",
    )
    c.set_defaults(func=show_env)


def show_env(parser, args):
    """Main method to show the current environment variables created by ggd for the specific conda environment

    show_env
    ========
    This method is used to show the ggd environment variables created during a ggd package installation 
     in the current conda environemnt. It will print out the active and inactive environment variables 
     and indicate how to active inactive environment variables.
    """
    import sys

    pattern = args.pattern if args.pattern else ".*"
    conda_env, conda_path = get_conda_env()
    env_filename = os.path.join(conda_path, "etc", "conda", "activate.d", "env_vars.sh")
    env_vars = {}
    try:
        with open(env_filename, "r") as env_file:
            for var in env_file:
                # parsing with checks in case there is a nonstandard/corrupt line in env file
                var_array = var.strip().split()
                if len(var_array) >= 2:
                    var_item_array = var_array[1].split("=")
                    if len(var_item_array) >= 1:
                        env_vars[var_item_array[0]] = var_item_array[1]
        matching_vars = {}
        print("*****************************\n")
        for env_var in env_vars:
            try:
                if re.search(pattern, env_var):
                    matching_vars[env_var] = env_vars[env_var]
            except:
                print("Invalid pattern")
                sys.exit(1)
        active_vars, inactive_vars = test_vars(matching_vars)

        if len(active_vars) > 0:
            print("Active environment variables:")
            for active_var in sorted(active_vars):
                print("> $" + active_var)
            print()
        if len(inactive_vars) > 0:
            print("Inactive or out-of-date environment variables:")
            for inactive_var in sorted(inactive_vars):
                print("> $" + inactive_var)
            # print ("\nTo activate inactive or out-of-date vars, run:\nsource activate %s\n" % conda_env)
            print(
                "\nTo activate inactive or out-of-date vars, run:\nsource activate %s\n"
                % "base"
            )
        if not active_vars and not inactive_vars:
            raise ValueError
    except (IOError, ValueError):
        print("No matching recipe variables found for this environment")
    finally:
        print("*****************************\n")


def remove_env_variable(env_var, prefix=None):
    """Method to remove an environment variable if the files are removed from the system

    remove_env_variable
    ===================
    This method is used to remove an environment variable from the activate.d/env_var.sh and
    deactivate.d/env_var.sh files during an uninstall.

    Parameters:
    -----------
    1) env_var: The environment variable to remove
    2) prefix: The conda environment/prefix to remove the environment var from
    """

    from .utils import conda_root

    target_prefix = conda_root() if prefix == None else prefix

    env_var = env_var.replace("-", "_")
    print("\n:ggd:env: Removing the %s environment variable" % env_var)
    conda_env, conda_path = get_conda_env(target_prefix)
    active_env_file = os.path.join(
        conda_path, "etc", "conda", "activate.d", "env_vars.sh"
    )
    deactive_env_file = os.path.join(
        conda_path, "etc", "conda", "deactivate.d", "env_vars.sh"
    )
    var_list = []
    with open(active_env_file, "r") as active_env:
        for var in active_env:
            if not re.search(r"\b" + env_var + "=", var):
                var_list.append(var.strip())
    with open(active_env_file, "w") as new_active_env:
        for var in var_list:
            new_active_env.write(var + "\n")
    var_list = []
    with open(deactive_env_file, "r") as deactive_env:
        for var in deactive_env:
            if not re.search(r"\b" + env_var + r"\b", var):
                var_list.append(var.strip())
    with open(deactive_env_file, "w") as new_deactive_env:
        for var in var_list:
            new_deactive_env.write(var + "\n")


def activate_environment_variables():
    """Method to activate the current environment variables

    acticate_environment_variables
    ==============================
    This method is used to activate the environments in the current active environment 
    """
    import subprocess as sp
    from argparse import Namespace

    conda_env, conda_path = get_conda_env()
    #    sp.check_output(["activate", "base"])
    show_env((), Namespace(command="show-env", pattern=None))


def test_vars(env_vars):
    """Method to identify the active and inactive environment variables for a specific conda environment

    test_vars
    =========
    This mehtod is used to get the active and inactive environment variables for a specific conda environment
     created by ggd.

    Parameters:
    -----------
    1) env_vars: The list of environment variables to check for activity  

    Return:
    +++++++
    1) A list of the active environment variables
    2) A list of the inactive environment variables
    """

    active_vars = []
    inactive_vars = []

    for env_var in env_vars:
        if env_var in os.environ and os.environ[env_var] == env_vars[env_var]:
            active_vars.append(env_var)
        else:
            inactive_vars.append(env_var)
    return active_vars, inactive_vars
