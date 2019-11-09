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
        description="Get a predicted install file path for a data package before it is installed. (Use for worklows, such as Snakemake)",
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
        help="(Optional) The name or the full directory path to an conda environment. The predicted path will be based on this conda environment. When installing, the data package should also be installed in this environment. (Only needed if not predicting for a path in the current conda enviroment)",
    )
    c2 = c.add_argument_group("required arguments")
    c2.add_argument(
        "-pn",
        "--package-name",
        required=True,
        help="(Required) The name of the data package to predict a file path for",
    )
    c2.add_argument(
        "-fn",
        "--file-name",
        required=True,
        help="(Required) The name of the file to predict that path for. It is best if you give the full and correct name of the file to predict the path for. If not, ggd will try to identify the right file, but won't guarantee that it is the rigth file",
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
    1) ggd_channel: The name of the ggd-channel to look in
     
    Return:
    +++++++
    1) GGD metadata as a dictionary

    """
    from .utils import check_for_internet_connection, get_channeldata_url
    from .search import load_json_from_url

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
    from .utils import conda_root, get_conda_prefix_path, prefix_in_conda

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

    ## Get path information
    species = metadata_dict["packages"][args.package_name]["identifiers"]["species"]
    build = metadata_dict["packages"][args.package_name]["identifiers"]["genome-build"]
    version = metadata_dict["packages"][args.package_name]["version"]

    ## Print the path
    path = os.path.join(
        CONDA_ROOT,
        "share",
        "ggd",
        species,
        build,
        args.package_name,
        version,
        file_name,
    )
    print(path)


