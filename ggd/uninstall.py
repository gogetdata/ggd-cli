# -------------------------------------------------------------------------------------------------------------
## Import Statements
# -------------------------------------------------------------------------------------------------------------
from __future__ import print_function

import os
import shutil
import subprocess as sp
import sys

from .utils import conda_root, get_ggd_channels


# -------------------------------------------------------------------------------------------------------------
## Argument Parser
# -------------------------------------------------------------------------------------------------------------
def add_uninstall(p):
    c = p.add_parser(
        "uninstall",
        help="Uninstall a ggd data package",
        description="Use ggd to uninstall a ggd data package installed in the current conda environment",
    )
    c.add_argument(
        "-c",
        "--channel",
        default="genomics",
        choices=get_ggd_channels(),
        help="The ggd channel of the recipe to uninstall. (Default = genomics)",
    )
    c.add_argument("names", 
                   nargs = "+",
                   help="the name(s) of the ggd package(s) to uninstall"
    )

    c.set_defaults(func=uninstall)


# -------------------------------------------------------------------------------------------------------------
## Functions/Methods
# -------------------------------------------------------------------------------------------------------------


def get_channeldata(ggd_recipes, ggd_channel):
    """Method to get the conda channel data for the specific ggd/conda channel for the designated ggd recipe

    get_channeldata
    ===============
    Method to get the channel data and check if the recipe is within that channel.
     This method is to identify the files installed during installation, but that 
     won't be removed by normal uninstalling. These files will be removed by the 
     check_for_installation() method if it is found within the channeldata.json file

    """
    from .search import load_json, load_json_from_url, search_packages
    from .utils import (
        check_for_internet_connection,
        get_channel_data,
        get_channeldata_url,
    )

    jdict = {"channeldata_version": 1, "packages": {}}
    if check_for_internet_connection():
        CHANNEL_DATA_URL = get_channeldata_url(ggd_channel)
        jdict = load_json_from_url(CHANNEL_DATA_URL)
        ## Remove the ggd key if it exists
        ggd_key = jdict["packages"].pop("ggd", None)
    else:
        try:
            ## If no internet connection just load from the local file
            jdict = load_json(get_channel_data(ggd_channel))
            ## Remove the ggd key if it exists
            ggd_key = jdict["packages"].pop("ggd", None)
        except:
            pass

    package_list = []
    if len(jdict["packages"].keys()) > 0:
        package_list = search_packages(jdict, ggd_recipes)
    
    uninstall_recipes = True
    for recipe in ggd_recipes:
        if recipe not in package_list:
            uninstall_recipes = False
            print(
                "\n:ggd:uninstall: %s is not in the ggd-%s channel"
                % (recipe, ggd_channel)
            )
            similar_pkgs = get_similar_pkg_installed_by_conda(recipe)
            if len(similar_pkgs) > 0:
                print(
                    "\n:ggd:uninstall: Packages installed on your system that are similar include:\n\t\t Package\tChannel\n\t\t-%s"
                    % "\n\t\t-".join([x for x in similar_pkgs.split("\n")])
                )
                print(
                    "\n:ggd:uninstall: If one of these packages is the desired package to uninstall please re-run ggd uninstall with the desired package name and correct ggd channel name"
                )
                print(
                    "\n:ggd:uninstall: Note: If the the package is not a part of a ggd channel run 'conda uninstall <pkg>' to uninstall"
                )
                print(
                    "\n:ggd:uninstall:\t GGD channels include: %s"
                    % ",".join(get_ggd_channels())
                )
            else:
                print(
                    "\n:ggd:uninstall: Unable to find any package similar to the package entered. Use 'ggd search' or 'conda find' to identify the right package"
                )
                print("\n:ggd:uninstall: This package may not be installed on your system")

    if uninstall_recipes:
        return jdict
    else:
        return False


def get_similar_pkg_installed_by_conda(ggd_recipe):
    """Method to get a list of similarly installed package names, referring to package installed by conda

    get_similar_pkg_installed_by_conda
    ==================================
    Method to identify if there are similar packages to the one provided installed by conda that could be 
     uninstalled. Provides a list of potential pkg names
     
    Parameters:
    ----------
    1) ggd_recipe: The ggd_recipe name. (May not be an actually ggd_recipe)
     
    Returns:
    +++++++
    A string of pkgs and channels, with each pkg-channel separated from another by a new line
    """

    conda_package_list = sp.check_output(["conda", "list"]).decode("utf8").split("\n")
    ## Index 0 = name, index -1 = channel name
    return "\n".join(
        [
            pkg.split(" ")[0] + "\t" + pkg.split(" ")[-1]
            for pkg in conda_package_list
            if ggd_recipe in pkg
        ]
    )


def check_conda_installation(ggd_recipes,installed_ggd_packages):
    """Method to check if the ggd package was installed with conda

    check_conda_installation
    ========================
    Method used to check if the recipe has been installed with conda. If so, it uses conda to uninstall the recipe
    """
    
    ## Filter ggd recipe list to those installed by conda
    conda_installed_recipes = [x for x in ggd_recipes if x in installed_ggd_packages]
        
    ## Uninstall any conda installed recipes
    if len(conda_installed_recipes) > 0:
        print("\n:ggd:uninstall: %s are installed by conda on your system" % ", ".join(conda_installed_recipes))
        return(conda_uninstall(conda_installed_recipes))
    else:
        print("\n:ggd:uninstall: %s is NOT installed on your system" % ", ".join(ggd_recipes))


def conda_uninstall(ggd_recipes):
    """Method use to uninstall the ggd recipe using conda

    conda_uninstall
    ===============
    Method used to uninstall ggd recipe using conda
    """

    print("\n:ggd:uninstall: Uninstalling %s" % ", ".join(ggd_recipes))
    try:
        return sp.check_call(
            ["conda", "remove", "-y"] + ggd_recipes,
            stderr=sys.stderr,
            stdout=sys.stdout,
        )
    except sp.CalledProcessError as e:
        sys.stderr.write("ERROR in uninstall %s" % ", ".join(ggd_recipes))
        sys.stderr.write(str(e))
        sys.exit(e.returncode)


def check_for_installation(ggd_recipes, ggd_jdict, prefix=conda_root()):
    """Method to check for and processes ggd package if it is installed

    check_for_installation
    =================
    Method used to remove extra files created during recipe installation, but that are not 
     removed during normal uninstallation. 
    This method depends on the get_channeldata method. If the recipe is not found in the 
     channeldata.json file the extra files will not be removed. 
    
    Parameters:
    -----------
    1) ggd_recipes: A list of ggd recipe names to check for installation. (Recipes being uninstalled)
    2) ggd_jdict: The json dictionary describing the ggd recipe
    3) prefix: The conda prefix/environment to uninstall from (Default = conda_root())
    
    Returns:
    +++++++
    1) True for False: Whether or not to update the ggd package list
    """

    import glob
    from .show_env import remove_env_variable
    from .utils import conda_root, get_conda_prefix_path

    recipes_removed_from_conda = False
    for ggd_recipe in ggd_recipes:
        species = ggd_jdict["packages"][ggd_recipe]["identifiers"]["species"]
        build = ggd_jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
        version = ggd_jdict["packages"][ggd_recipe]["version"]

        prefix = get_conda_prefix_path(prefix) if prefix != conda_root() else prefix
        path = os.path.join(prefix, "share", "ggd", species, build, ggd_recipe, version)
        recipe_exists = glob.glob(path)
        if recipe_exists:
            print(
                "\n:ggd:uninstall: Removing %s version %s file(s) from ggd recipe storage"
                % (ggd_recipe, str(version))
            )
            shutil.rmtree(path)
            remove_from_condaroot(ggd_recipe, version, prefix)
            dir_env_var = "ggd_" + ggd_recipe + "_dir"
            remove_env_variable(dir_env_var, prefix)
            file_env_var = "ggd_" + ggd_recipe + "_file"
            remove_env_variable(file_env_var, prefix)
            recipes_removed_from_conda = True
        else:
            print("\n:ggd:uninstall: %s is not in the ggd recipe storage" % ggd_recipe)
    return recipes_removed_from_conda


def remove_from_condaroot(ggd_recipe, version, prefix):
    """Method to use conda to remove an installed ggd package from the conda root. This is a method for ggd package file handling

    remove_from_condaroot
    ====================
    Method used to remove the recipe's extra files created during installation, but that are not removed 
     when conda uninstalled. 
    """
    from .utils import update_installed_pkg_metadata

    ## Get a list of files for the package starting at the prefix path
    find_list = (
        sp.check_output(
            ["find", prefix, "-name", ggd_recipe + "-" + str(version) + "*"]
        )
        .decode("utf8")
        .strip()
        .split("\n")
    )
    ## Filter the list by conda env
    filtered_list = []
    for path in find_list:
        if prefix in path:
            if (
                str(prefix) + "/envs/" not in path
            ):  ## If the conda env root is in the path, and conda env root/env/ is not in the path, then add it to the filtered list
                filtered_list.append(path)
    print(
        "\n:ggd:uninstall: Deleting %d items of %s version %s from your conda root"
        % (len(filtered_list), ggd_recipe, version)
    )
    ## Remove files
    for path in filtered_list:
        if str(prefix) + "/env/" not in path:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    ## Update installed package list
    print("\n:ggd:uninstall: Updating installed package list")
    update_installed_pkg_metadata(prefix=prefix, exclude_pkg=ggd_recipe)


def uninstall(parser, args):
    """Main method for uninstall command

    uninstall
    =========
    Main method used to check if the recipe is installed, uninstall the recipe, and remove extra recipe files
    """
    from .utils import get_conda_package_list, get_run_deps_from_tar

    ## List of packages to uninstall
    ggd_recipes = args.names

    ## Get the channeldata.json file in dictionary form
    print("\n:ggd:uninstall: Checking for installation of: %s" % ", ".join(ggd_recipes))
    ggd_jsonDict = get_channeldata(ggd_recipes, args.channel)
    if ggd_jsonDict == False:
        sys.exit()

    ## Get the installed ggd data package names
    installed_ggd_packages = get_conda_package_list(conda_root())

    ## Check for GGD package as run deps
    ### Add them to the uninstall list
    ggd_info_dir = os.path.join(conda_root(), "share", "ggd_info", "noarch")
    tars_in_info_dir = set(os.listdir(ggd_info_dir))
    for recipe in args.names: 
        tarballfile = "{}-{}-{}.tar.bz2".format(recipe, installed_ggd_packages[recipe]["version"], installed_ggd_packages[recipe]["build"]) if recipe in installed_ggd_packages else ""
        if tarballfile in tars_in_info_dir:
            tarfile_path = os.path.join(ggd_info_dir,tarballfile) 
            ggd_recipes.extend(get_run_deps_from_tar(tarfile_path, args.channel))

    ## Check if installed through conda
    check_conda_installation(ggd_recipes,installed_ggd_packages.keys())

    ## Check if the recipe is in file system
    if len(ggd_jsonDict) > 0:
        check_for_installation(ggd_recipes, ggd_jsonDict)

    else:
        print("\n:ggd:uninstall: Skipping steps for package removal from system")

    print("\n:ggd:uninstall: DONE")

    return True
