# -------------------------------------------------------------------------------------------------------------
## Import Statements
# -------------------------------------------------------------------------------------------------------------
from __future__ import print_function

import os
import sys

from .utils import get_builds, get_ggd_channels, get_species

SPECIES_LIST = sorted(get_species())
GENOME_BUILDS = sorted(get_builds("*"))

# -------------------------------------------------------------------------------------------------------------
## Argument Parser
# -------------------------------------------------------------------------------------------------------------
def add_list_files(p):

    c = p.add_parser(
        "get-files",
        help="Get the data files for a specific installed ggd data package",
        description="Get a list of file(s) for a specific installed ggd package",
    )
    c.add_argument(
        "-c",
        "--channel",
        default="genomics",
        choices=get_ggd_channels(),
        help="The ggd channel of the recipe to find. (Default = genomics)",
    )
    c.add_argument(
        "-s",
        "--species",
        help="(Optional) species recipe is for. Use '*' for any species",
        choices=[str(x) for x in SPECIES_LIST],
    )
    c.add_argument(
        "-g",
        "--genome-build",
        choices=[str(x) for x in GENOME_BUILDS],
        help="(Optional) genome build the recipe is for. Use '*' for any genome build.",
    )
    c.add_argument(
        "-v",
        "--version",
        help="(Optional) pattern to match the version of the file desired. Use '*' for any version",
    )
    c.add_argument(
        "-p",
        "--pattern",
        help="(Optional) pattern to match the name of the file desired. To list all files for a ggd package, do not use the -p option",
    )
    c.add_argument(
        "--prefix",
        default=None,
        help="(Optional) The name or the full directory path to an conda environment where a ggd recipe is stored. (Only needed if not getting file paths for files in the current conda enviroment)",
    )
    c.add_argument(
        "name",
        help="pattern to match recipe name(s)."
    )
    c.set_defaults(func=list_files)


# -------------------------------------------------------------------------------------------------------------
## Functions/Methods
# -------------------------------------------------------------------------------------------------------------


def in_ggd_channel(ggd_recipe, ggd_channel):
    """Method to check if the desired ggd recipe is in the ggd channel

    in_ggd_channel
    ==============
    Method used to identify in the desired pacakge is in the ggd-<channel>.
     If it is the the species, build, and version is returned. 
     If it is not, then a few alternative package names are provided
     
    Parameters:
    ----------
    1) ggd_recipe: The name of the ggd recipe
    2) ggd_channel: The name of the ggd-channel to look in
     
    Return:
    +++++++
    1) species: The species for the ggd-recipe
    2) build: The genome build for the ggd-recipe
    3) version: The version of the ggd-recipe

    """

    from .search import load_json, load_json_from_url, search_packages
    from .utils import (
        check_for_internet_connection,
        get_channel_data,
        get_channeldata_url,
    )

    json_dict = {"channeldata_version": 1, "packages": {}}
    if check_for_internet_connection(3):
        CHANNELDATA_URL = get_channeldata_url(ggd_channel)
        json_dict = load_json_from_url(CHANNELDATA_URL)

        ## Remove the ggd key if it exists
        ggd_key = json_dict["packages"].pop("ggd", None)

    else:
        try:
            ## If no internet connection just load from the local file
            json_dict = load_json(get_channel_data(ggd_channel))
            ## Remove the ggd key if it exists
            ggd_key = json_dict["packages"].pop("ggd", None)
        except:
            pass

    package_list = []
    if len(json_dict["packages"].keys()) > 0:
        package_list = search_packages(json_dict, [ggd_recipe])


    if ggd_recipe in package_list:
        species = json_dict["packages"][ggd_recipe]["identifiers"]["species"]
        build = json_dict["packages"][ggd_recipe]["identifiers"]["genome-build"]
        version = json_dict["packages"][ggd_recipe]["version"]
        return (species, build, version)
    else:
        print(
            "\n:ggd:get-files: %s is not in the ggd-%s channel"
            % (ggd_recipe, ggd_channel)
        )
        print(
            "\n:ggd:get-files:\t Similar recipes include: \n\t- {recipe}".format(
                recipe="\n\t- ".join(package_list[0:5])
            )
        )
        sys.exit(2)


def list_files(parser, args):
    """Main method. Method used to list files for an installed ggd-recipe"""

    import glob
    from .utils import (
        conda_root,
        get_conda_prefix_path,
        prefix_in_conda,
        validate_build,
    )

    CONDA_ROOT = (
        get_conda_prefix_path(args.prefix)
        if args.prefix != None and prefix_in_conda(args.prefix)
        else conda_root()
    )

    name = args.name
    channeldata_species, channeldata_build, channeldata_version = in_ggd_channel(
        args.name, args.channel
    )
    species = args.species if args.species else channeldata_species
    build = args.genome_build if args.genome_build else channeldata_build
    if not validate_build(build, species):
        sys.exit(3)
    version = args.version if args.version else "*"
    pattern = args.pattern if args.pattern else "*"

    path = os.path.join(
        CONDA_ROOT, "share", "ggd", species, build, name, version, pattern
    )
    files = glob.glob(path)
    if files:
        print("\n".join(files))
    else:
        print(
            "\n:ggd:get-files: No matching files found for %s" % args.name,
            file=sys.stderr,
        )
        sys.exit(1)
