# -------------------------------------------------------------------------------------------------------------
## Import Statements
# -------------------------------------------------------------------------------------------------------------
from __future__ import print_function

import sys

from .utils import get_ggd_channels


# -------------------------------------------------------------------------------------------------------------
## Argument Parser
# -------------------------------------------------------------------------------------------------------------
def add_predict_path(p):

    c = p.add_parser(
        "predict-path",
        help="Predict the install file path of a data package that hasn't been installed yet. (Use for workflows, such as Snakemake)",
        description="Get a predicted install file path for a data package before it is installed. (Use for workflows, such as Snakemake)",
    )

    c.add_argument(
        "-c",
        "--channel",
        default="genomics",
        choices=[str(x) for x in get_ggd_channels()],
        help="The ggd channel of the recipe to find. (Default = genomics)",

    )
    c.add_argument(
        "--prefix",
        default=None,
        help="(Optional) The name or the full directory path to an conda environment. The predicted path will be based on this conda environment. When installing, the data package should also be installed in this environment. (Only needed if not predicting for a path in the current conda environment)",
    )

    c.add_argument(
        "--id",
        metavar="meta-recipe ID",
        default = None,
        help = "(Optional) The ID to predict the path for if the package is a meta-recipe. If it is not a meta-recipe it will be ignored"
    )

    c2 = c.add_argument_group("One Argument Required")

    c2.add_argument(

        "--dir-path",
        action="store_true",
        help = "(Required if '--file-name' not used) Whether or not to get the predicted directory path rather then the predicted file path. If both --file-name and --dir-path are provided the --file-name will be used and --dir-path will be ignored", 
    )

    c2.add_argument(
        "-fn",
        "--file-name",
        default = None,
        help="(Required if '--dir-path' not used) The name of the file to predict that path for. It is best if you give the full and correct name of the file to predict the path for. If not, ggd will try to identify the right file, but won't guarantee that it is the right file",
    )

    c3 = c.add_argument_group("Required Arguments")

    c3.add_argument(
        "-pn",
        "--package-name",
        required=True,
        help="(Required) The name of the data package to predict a file path for",
    )

    c.set_defaults(func=predict_path)


# -------------------------------------------------------------------------------------------------------------
## Functions/Methods
# -------------------------------------------------------------------------------------------------------------


def get_ggd_metadata(ggd_channel):
    """Method to get the ggd metadata by ggd channel

    in_ggd_channel
    ==============
    Method to get the metadata file for a specific ggd channel
     this method will exit if internet access is not available
     
    Parameters:
    ----------
    1) ggd_channel: (str) The name of the ggd-channel to look in
     
    Return:
    +++++++
    1) (dict) GGD metadata as a dictionary

    """
    from .search import load_json_from_url
    from .utils import check_for_internet_connection, get_channeldata_url

    json_dict = {"channeldata_version": 1, "packages": {}}
    if check_for_internet_connection(3):
        CHANNELDATA_URL = get_channeldata_url(ggd_channel)
        json_dict = load_json_from_url(CHANNELDATA_URL)
    else:
        ## If no internet connection
        sys.exit(
            "\n:ggd:predict-path: A internet connection is required to use this function. Please try again when you have secured an internet connection\n"
        )

    return json_dict


def predict_path(parser, args):
    """ Main method. Method used to predict the installed data file path for a data file that has not bee installed yet"""
    import os
    import re

    from .utils import check_for_meta_recipes, conda_root, get_conda_prefix_path, prefix_in_conda
    from .install import get_idname_from_metarecipe

    if not args.dir_path and args.file_name is None:
        print(":ggd:predict-path: !!ERROR!! Either the '--file-name' or the '--dir-path' argument is required. Neither was given")
        sys.exit()

    ## get prefix
    CONDA_ROOT = (
        get_conda_prefix_path(args.prefix)
        if args.prefix != None and prefix_in_conda(args.prefix)
        else conda_root()
    )

    ## Get metadata
    metadata_dict = get_ggd_metadata(args.channel)

    ## Check the package is in the metadata
    if args.package_name not in metadata_dict["packages"]:
        sys.exit(
            "\n:ggd:predict-path: The {pn} data package is not one of the packages in the ggd-{c} channel\n".format(
                pn=args.package_name, c=args.channel
            )
        )

    if args.file_name is not None:

        ## Check there is a "final-files" in the metadata for the package
        if (
            "final-files" not in metadata_dict["packages"][args.package_name]["tags"]
            or len(
                metadata_dict["packages"][args.package_name]["tags"].get("final-files", [])
            )
            == 0
        ):
            sys.exit(
                "\n:ggd:predict-path: The {p} data package does not have the final data files listed. This packages needs to be updated. To update, contact the GoGetData team at https://github.com/gogetdata/ggd-recipes\n".format(
                    p=args.package_name
                )
            )

        ## Check that the file is one of the final-files listed in the metadata
        if (
            args.file_name
            not in metadata_dict["packages"][args.package_name]["tags"]["final-files"]
        ):
            matching_files = [
                x
                for x in metadata_dict["packages"][args.package_name]["tags"]["final-files"]
                if re.search(args.file_name, x)
            ]
            if len(matching_files) > 0:
                ## Chose the first file that matched
                file_name = matching_files[0]
            else:
                sys.exit(
                    "\n:ggd:predict-path: The {f} file is not one of the files listed for this package. The files installed by this package are: \n\t\t{fo}".format(
                        f=args.file_name,
                        fo="\n\t\t".join(
                            metadata_dict["packages"][args.package_name]["tags"][
                                "final-files"
                            ]
                        ),
                    )
                )
        else:
            file_name = args.file_name

    elif args.dir_path:
        file_name = ""
        

    ## Get path information
    species = metadata_dict["packages"][args.package_name]["identifiers"]["species"]
    build = metadata_dict["packages"][args.package_name]["identifiers"]["genome-build"]
    version = metadata_dict["packages"][args.package_name]["version"]

    name = args.package_name if not check_for_meta_recipes(args.package_name, metadata_dict) else get_idname_from_metarecipe(args.id.lower(), args.package_name, metadata_dict) if args.id is not None else args.package_name 

    ## Print the path
    path = os.path.join(
        CONDA_ROOT,
        "share",
        "ggd",
        species,
        build,
        name,
        version,
        file_name,
    )
    print(path)
