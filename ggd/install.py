# -------------------------------------------------------------------------------------------------------------
## Import Statements
# -------------------------------------------------------------------------------------------------------------
from __future__ import print_function

import glob
import os
import shutil
import subprocess as sp
import sys
import traceback

from .utils import conda_root, get_ggd_channels


# -------------------------------------------------------------------------------------------------------------
## Argument Parser
# -------------------------------------------------------------------------------------------------------------
def add_install(p):

    c = p.add_parser(
        "install",
        help="Install a ggd data package",
        description="Install a ggd data package into the current or specified conda environment",
    )
    c.add_argument(
        "-c",
        "--channel",
        default="genomics",
        choices=get_ggd_channels(),
        help="The ggd channel the desired recipe is stored in. (Default = genomics)",
    )
    c.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="(Optional) When the -d flag is set debug output will be printed to stdout.",
    )
    c.add_argument(
        "--file",
        default=[],
        action="append",
        help="A file with a list of ggd data packages to install. One package per line. Can use more than one (e.g. ggd install --file <file_1> --file <file_2> )",
    )
    c.add_argument(
        "name",
        nargs="*",
        help="The data package name to install. Can use more than once (e.g. ggd install <pkg 1> <pkg 2> <pkg 3> ). (NOTE: No need to designate version as it is implicated in the package name)",
    )
    c.add_argument(
        "--prefix",
        default=None,
        help="(Optional) The name or the full directory path to an existing conda environment where you want to install a ggd data pacakge. (Only needed if you want to install the data package into a different conda environment then the one you are currently in)",
    )
    c.set_defaults(func=install)


# -------------------------------------------------------------------------------------------------------------
## Functions/Methods
# -------------------------------------------------------------------------------------------------------------


def check_ggd_recipe(ggd_recipe, ggd_channel):
    """Method used to check if the desired package is in the ggd repo using the repo metadata file

    check_ggd_recipe
    ================
    Method to check if the ggd recipe exists. Uses search_packages from search.py to 
     search the ggd-channel json file. If the recipe exists within the json file,
     the installation proceeds. If not, the instalation stops

    Parmaters:
    ----------
    1) ggd_recipe: The name of a ggd-recipe:
    2) ggd_channel: The name of a ggd channel (specific for metadata)

    Returns:
    1) A dictionary of the metadata file for the channel the recipe is in
    or 
    2) None if the recipe does not exists in the channel
    """
    from .search import load_json_from_url, search_packages
    from .utils import get_channeldata_url

    CHANNEL_DATA_URL = get_channeldata_url(ggd_channel)
    ## Get ggd repodata
    jdict = load_json_from_url(CHANNEL_DATA_URL)
    ## Remove the ggd key if it exists
    ggd_key = jdict["packages"].pop("ggd", None)

    package_list = search_packages(jdict, [ggd_recipe])


    if ggd_recipe in package_list:
        print(
            "\n:ggd:install: %s exists in the ggd-%s channel"
            % (ggd_recipe, ggd_channel)
        )
        return jdict
    else:
        print(
            "\n:ggd:install: '%s' was not found in ggd-%s" % (ggd_recipe, ggd_channel)
        )
        print(
            ":ggd:install:\t You can search for recipes using the ggd search tool: \n\t\t'ggd search %s'\n"
            % ggd_recipe
        )
        return None


def check_if_installed(ggd_recipe, ggd_jdict, prefix=None):
    """Method to check if the recipe has already been installed and is in the conda ggd storage path. 
        
    check_if_installed
    ==================
    This method is used to check if the ggd package has been installed and is located in the ggd storage path.
     If it is already installed the installation stops. If it is not detected then installation continues.

    Parameters:
    -----------
    1) ggd_recipe: The name of a recipe to check if it is installed or not
    2) ggd_jdict: The channel specific metadata file as a dictionary 
    3) prefix: The prefix/conda environment to check in
    
    Retruns:
    1) False if not installed
    2) True if it is installed
    """

    species = ggd_jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_recipe]["version"]

    CONDA_ROOT = prefix if prefix != None else conda_root()

    path = os.path.join(CONDA_ROOT, "share", "ggd", species, build, ggd_recipe, version)
    recipe_exists = glob.glob(path)
    if recipe_exists:
        print("\n:ggd:install: '%s' is already installed." % ggd_recipe)
        print(":ggd:install:\t You can find %s here: %s\n" % (ggd_recipe, path))
        return True
    else:
        print(
            "\n:ggd:install: %s version %s is not installed on your system"
            % (ggd_recipe, version)
        )
        return False


def check_conda_installation(ggd_recipe, prefix=None):
    """Method used to check if the recipe has been installed using conda.

    check_conda_installation
    ========================
    This method is used to check if the ggd data package has been installed by the conda system,
     without being installed by the ggd system. If it has, the recipe needs to be uninstalled and 
     reinstalled. If not, the system continues to install the package using ggd.

    Parameters:
    -----------
    1) ggd_recipe: The name of a ggd package to check if it has been installed by conda
    2) prefix: The conda environment/prefix to check in

    Returns:
    ++++++++
    1) False if it has not been installed
    2) sys.exit() if it has been installed. (Which means it hasn't been installed by ggd and needs to be uninstalled before
           proceding)
    """
    from .utils import get_conda_package_list

    ## Get the target prefix
    target_prefix = prefix if prefix != None else conda_root()
    conda_package_list = get_conda_package_list(
        target_prefix
    )  ## Get a list of installed ggd packages using conda list

    if ggd_recipe not in conda_package_list.keys():
        print("\n:ggd:install: %s has not been installed by conda" % ggd_recipe)
        return False
    else:
        print(
            "\n:ggd:install: %s has been installed by conda on your system and must be uninstalled to proceed."
            % ggd_recipe
        )
        print(
            ":ggd:install:\t To reinstall run:\n\t\t $ ggd uninstall %s \n\t\t $ ggd install %s"
            % (ggd_recipe, ggd_recipe)
        )
        if prefix != conda_root():
            print(
                ":ggd:install:\t NOTE: You must activate the conda prefix {p} before running the uninstall command".format(
                    p=target_prefix
                )
            )
        sys.exit()


def check_S3_bucket(ggd_recipe, ggd_jdict):
    """Method to check if the recipe is stored on the ggd S3 bucket. If so it installs from S3

    check_S3_bucket
    ==============
    This method is used to check if the recipe has been cached on aws S3 bucket. It returns true if the 
     the recipe is cached, and false if it is not. If it is cached the cached version will be installed. 

    Parameters:
    -----------
    1) ggd_recipe: The name of a recipe to check if it is installed or not
    2) ggd_jdict: The channel specific metadata file as a dictionary 

    Returns:
    ++++++++
    1) True if the recipe has been cached
    2) False if not
    """

    if "tags" in ggd_jdict["packages"][ggd_recipe]:
        if "cached" in ggd_jdict["packages"][ggd_recipe]["tags"]:
            if "uploaded_to_aws" in ggd_jdict["packages"][ggd_recipe]["tags"]["cached"]:
                print(
                    "\n:ggd:install: The %s package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket"
                    % ggd_recipe
                )
                return True
    return False


def install_from_cached(ggd_recipes, ggd_channel, ggd_jdict, debug=False, prefix=None):
    """Method to install the ggd data package using a cached recipe

    install_from_cached
    ===================
    This method is used to install a ggd data package from a cached location. That is, a cached ggd recipe has 
     been created and can be installed. Installing using a cached recipe increases the install speed. This is
     because (1) data processing and curation has already been done and the resulting files are cached. (This removes
     the time it takes to processes the data). (2) With a cached recipe we can bypass conda's solve environment step. 

    If installed correctly the method returns True

    Parameters:
    ----------
    1) ggd_recipes: A list of ggd recipes that are cached to install
    2) ggd_channel: The ggd channel for the recipes
    3) ggd_jdict: The metadata json dictionary for the ggd recipes
    4) debug: Whether to show debug output or not
    5) prefix: THe prefix/conda environment to install into

    Returns:
    +++++++
    True if successful install
    """
    from .utils import (
        bypass_satsolver_on_install,
        update_installed_pkg_metadata,
        ChecksumError,
    )

    conda_channel = "ggd-" + ggd_channel
    try:
        ##Install
        bypass_satsolver_on_install(ggd_recipes, conda_channel, debug, prefix)

    except Exception as e:
        from .uninstall import check_for_installation

        print(
            "\n:ggd:install: %s did not install properly. Review the error message:\n"
            % ", ".join(ggd_recipes)
        )
        print(str(e))
        print(traceback.format_exc())
        target_prefix = conda_root() if prefix == None else prefix
        check_for_installation(
            ggd_recipes, ggd_jdict, target_prefix
        )  ## .uninstall method to remove extra ggd files
        print(
            "\n:ggd:install: %s was not installed. Please correct the errors and try again."
            % ", ".join(ggd_recipes)
        )
        sys.exit(1)

    ## copy tarball and pkg file to target prefix
    if prefix != None and prefix != conda_root():
        print("\n:ggd:install: Updating package metadata in user defined prefix")
        copy_pkg_files_to_prefix(prefix, ggd_recipes)

    ## Update installed metadata
    print("\n:ggd:install: Updating installed package list")
    target_prefix = prefix if prefix != None else conda_root()
    update_installed_pkg_metadata(
        prefix=target_prefix, remove_old=False, add_packages=ggd_recipes
    )

    ## Checkusm
    try:
        install_checksum(ggd_recipes, ggd_jdict, target_prefix)
    except ChecksumError as e:
        from .uninstall import check_for_installation

        print(
            "\n:ggd:install: %s did not install properly. Review the error message:\n"
            % ", ".join(ggd_recipes)
        )
        print(str(e))
        print(traceback.format_exc())
        check_for_installation(
            ggd_recipes, ggd_jdict, target_prefix
        )  ## .uninstall method to remove extra ggd files
        print(
            "\n:ggd:install: %s was not installed. Please correct the errors and try again."
            % ", ".join(ggd_recipes)
        )
        sys.exit(1)

    print("\n:ggd:install: Install Complete")

    return True


def conda_install(ggd_recipes, ggd_channel, ggd_jdict, debug=False, prefix=None):
    """Method to install the recipe from the ggd-channel using conda
    
    conda_install
    ============
    This method is used to install the ggd recipe from the ggd conda channel using conda, if the files 
     have not been cached. 

    Parameters:
    ----------
    1) ggd_recipes: A list of ggd recipes that are cached to install
    2) ggd_channel: The ggd channel for the recipes
    3) ggd_jdict: The metadata json dictionary for the ggd recipes
    4) debug: Whether to show debug output or not
    5) prefix: THe prefix/conda environment to install into

    Returns:
    +++++++
    True if successful install
    """
    from .utils import (
        get_required_conda_version,
        update_installed_pkg_metadata,
        ChecksumError,
    )

    ## Get the target prefix
    target_prefix = prefix if prefix != None else conda_root()

    ## Get conda version
    conda_version, equals = get_required_conda_version()

    ## create install string
    conda_install_str = "\"" + "conda" + equals + str(conda_version) + "\"" 

    ## Add debug option
    conda_install_str += " --debug" if debug else ""

    try:
        ## py3 *args. (Syntax error in py2)
        # command = ["conda", "install", "-c", "ggd-"+ggd_channel, "-y", "--prefix", target_prefix, *ggd_recipes, conda_install_str]

        ## Install
        command = (
            [
                "conda",
                "install",
                "-c",
                "ggd-" + ggd_channel,
                "-y",
                "--prefix",
                target_prefix,
            ]
            + ggd_recipes
            + [conda_install_str]
        )
        sp.check_call(command, stderr=sys.stderr, stdout=sys.stdout)

    except sp.CalledProcessError as e:
        from .uninstall import check_for_installation

        sys.stderr.write(
            "\n:ggd:install: ERROR in install %s\n" % ", ".join(ggd_recipes)
        )
        sys.stderr.write(str(e))
        sys.stderr.write(
            "\n:ggd:install: Removing files created by ggd during installation"
        )
        check_for_installation(
            ggd_recipes, ggd_jdict, target_prefix
        )  ## .uninstall method to remove extra ggd files
        sys.exit(e.returncode)

    ## copy tarball and pkg file to target prefix
    if prefix != None and prefix != conda_root():
        copy_pkg_files_to_prefix(prefix, ggd_recipes)

    ## Update installed metadata
    print("\n:ggd:install: Updating installed package list")
    update_installed_pkg_metadata(
        prefix=target_prefix, remove_old=False, add_packages=ggd_recipes
    )

    ## Checkusm
    try:
        install_checksum(ggd_recipes, ggd_jdict, target_prefix)

    except ChecksumError as e:
        from .uninstall import check_for_installation

        sys.stderr.write(
            "\n:ggd:install: ERROR in install %s\n" % ", ".join(ggd_recipes)
        )
        sys.stderr.write(str(e))
        sys.stderr.write(
            "\n:ggd:install: Removing files created by ggd during installation"
        )
        check_for_installation(
            ggd_recipes, ggd_jdict, target_prefix
        )  ## .uninstall method to remove extra ggd files
        sys.exit(e.returncode)

    print("\n:ggd:install: Install Complete")

    return True


def get_file_locations(ggd_recipes, ggd_jdict, prefix=None):
    """Method used to print the location of the installed files

    get_file_locations
    ==================
    This method is used to print the location of the data files installed for a reference 
    for the user.

    Parameters:
    ----------
    1) ggd_recipes: A list of ggd package names to install
    2) ggd_jdict: ggd channel metadata as a dictionary 
    3) prefix: The conda prefix/environment the packages are being installed into
    """

    print("\n\n:ggd:install: Installed file locations")
    print(
        "======================================================================================================================"
    )
    header = "\n  {:>18s} {:^95s}".format("GGD Package", "Environment Variable(s)")
    dash = "     " + "-" * 100
    print(header)

    CONDA_ROOT = prefix if prefix != None else conda_root()
    for ggd_recipe in ggd_recipes:
        species = ggd_jdict["packages"][ggd_recipe]["identifiers"]["species"]
        build = ggd_jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
        version = ggd_jdict["packages"][ggd_recipe]["version"]
        path = os.path.join(
            CONDA_ROOT, "share", "ggd", species, build, ggd_recipe, version
        )

        try:
            assert os.path.exists(path)
        except AssertionError:
            print(dash)
            print("-> {:>18s}".format(ggd_recipe))
            print("\n:ggd:install: There was an error durring installation")
            continue

        dir_var = "$ggd_%s_dir" % ggd_recipe.replace("-", "_")
        file_var = ""
        if os.path.exists(path):
            files = os.listdir(path)
            if len(files) == 1:  ## A single file will have a env var
                file_var = "$ggd_%s_file" % ggd_recipe.replace("-", "_")
            elif (
                len(files) == 2
            ):  ## A file with an associated index will have a env var
                if [
                    True
                    for x in files
                    if ".tbi" in x
                    or ".bai" in x
                    or ".crai" in x
                    or ".fai" in x
                    or ".gzi" in x
                ]:
                    file_var = "$ggd_%s_file" % ggd_recipe.replace("-", "_").replace(
                        ".", "_"
                    )

        print(dash)
        if len(file_var) > 1:
            print("-> {:>18s} {:^85s}".format(ggd_recipe, dir_var))
            print("   {:>18s} {:^85s}".format(" " * len(ggd_recipe), file_var))
        else:
            print("-> {:>18s} {:^85s}".format(ggd_recipe, dir_var))

        print("\n\nInstall Path: %s\n\n" % path)

    print(dash, "\n")
    print(
        ":ggd:install: To activate environment variables run `source activate base` in the environmnet the packages were installed in\n"
    )
    if prefix != None:
        print(
            ":ggd:install: NOTE: These environment variables are specific to the %s conda environment and can only be accessed from within that environmnet"
            % prefix
        )
    print(
        "======================================================================================================================"
    )
    print("\n\n")


def install_checksum(pkg_names, ggd_jdict, prefix=conda_root()):
    """Method to check the md5sums of the installed files against the metadata md5sums

    install_checksum
    ================
    This method is used to run checksum on the installed files to make sure the contents of data files 
     was downloaded correctly 
    
    Parameters:
    -----------
    1) pkg_names: A list of the package names that were installed
    2) ggd_jdict: ggd channel metadata as a dictionary 
    3) prefix: The prefix the packages were installed into

    Retunrs:
    +++++++
    1) True if checksum passes
    2) raises "ChecksumError" if fails
    """
    import tarfile
    from .utils import (
        get_conda_package_list,
        get_checksum_dict_from_tar,
        data_file_checksum,
        ChecksumError,
    )

    print("\n:ggd:install: Initiating data file content validation using checksum")
    data_packages = get_conda_package_list(prefix, include_local=True)
    for pkg_name in pkg_names:
        print("\n:ggd:install: Checksum for {}".format(pkg_name))

        ## Get the file paths for the tar file and package
        version = str(data_packages[pkg_name]["version"])
        build = str(data_packages[pkg_name]["build"])
        tarfile_path = os.path.join(
            prefix, "pkgs", "{}-{}-{}.tar.bz2".format(pkg_name, version, build)
        )
        ## Check if checksum file exists
        with tarfile.open(tarfile_path, mode="r|bz2") as tar:
            if "info/recipe/checksums_file.txt" not in tar.getnames():
                print(
                    "\n:ggd:install: WARNING: Checksum file not available for the {} data package. Data file content validation will be skipped".format(
                        pkg_name
                    )
                )
                continue

        ## Get checksum dict
        checksum_dict = get_checksum_dict_from_tar(tarfile_path)

        ## Install path
        species = ggd_jdict["packages"][pkg_name]["identifiers"]["species"]
        build = ggd_jdict["packages"][pkg_name]["identifiers"]["genome-build"]
        version = ggd_jdict["packages"][pkg_name]["version"]
        install_path = os.path.join(
            prefix, "share", "ggd", species, build, pkg_name, version
        )

        try:
            assert os.path.exists(install_path)
        except AssertionError:
            print(
                "\n:ggd:install: !!ERROR!! There was an error durring the installation of {} and the files weren't installed correctly".format(
                    pkg_name
                )
            )
            raise ChecksumError(pkg_name)

        ## Preform checksum
        if not data_file_checksum(install_path, checksum_dict):
            print("\n:ggd:install: !!ERROR!! Checksum failed")
            raise ChecksumError(pkg_name)
        else:
            print(":ggd:install: ** Successful Checksum **")

    return True


def copy_pkg_files_to_prefix(prefix, pkg_names):
    """Method to copy the tar and package files from the current conda envrionment to the target prefix
    
    copy_pkg_files_to_prefix
    ========================
    This method is used to copy the tarball file and the pkg file from the current conda envrionment to the 
     target prefix if the prefix flag is set. This will support pkg info lookup for data managment when installing
     a package using the prefix flag

    Parameters:
    -----------
    1) prefix: The user set prefix 
    2) pkg_names: A list of he names of the packages being installed

    Returs:
    +++++++
    True: If files have been copied 
    False: If files were not copied (due to the prefix being the same as the current conda environment)
    Exception: If copying failed
    """
    from .utils import get_conda_package_list

    CONDA_ROOT = conda_root()

    ## Check that the prefix is not the same as the conda root
    if CONDA_ROOT == prefix:
        return False

    ## Create the path if it does not already exists
    if os.path.exists(os.path.join(prefix, "pkgs")) == False:
        os.mkdir(os.path.join(prefix, "pkgs"))

    data_packages = get_conda_package_list(prefix)
    for pkg_name in pkg_names:
        ## Get the file paths for the tar file and package
        version = str(data_packages[pkg_name]["version"])
        build = str(data_packages[pkg_name]["build"])

        tarfile_path = os.path.join(
            CONDA_ROOT, "pkgs", "{}-{}-{}.tar.bz2".format(pkg_name, version, build)
        )
        pkg_path = os.path.join(
            CONDA_ROOT, "pkgs", "{}-{}-{}".format(pkg_name, version, build)
        )

        ## Copy files to new location
        shutil.copy2(tarfile_path, os.path.join(prefix, "pkgs"))
        shutil.copytree(
            pkg_path,
            os.path.join(prefix, "pkgs", "{}-{}-{}".format(pkg_name, version, build)),
        )

    return True


def install(parser, args):
    """Main method for installing a ggd data package

    install
    =======
    This method is the main method for running ggd install. It controls the different levels of install
    and file handeling. 
    """

    ## If no package names are provided and no file is given, exit
    if not args.name and not args.file:
        sys.exit(
            "\n\n:ggd:install: !!ERROR!! Either a data package name, or a file name with --file, is required and was not supplied.\n"
        )

    ## Check the prefix is a real one
    from .utils import get_conda_prefix_path, prefix_in_conda

    if args.prefix != None:
        prefix_in_conda(args.prefix)
    else:
        args.prefix = conda_root()

    conda_prefix = get_conda_prefix_path(args.prefix)

    ## Get a list of packages
    pkg_list = args.name
    if args.file:
        for file in args.file:
            assert os.path.exists(
                file
            ), "\n\n:ggd:install: !!ERROR!! The {f} file provided does not exists".format(
                f=file
            )
            with open(file, "r") as f:
                pkg_list.extend(
                    [x.strip() for x in f if len(x.strip().split(" ")) == 1]
                )

    ## Check each package
    install_list = []
    for pkg in sorted(pkg_list):
        print(
            "\n\n:ggd:install: Looking for %s in the 'ggd-%s' channel"
            % (pkg, args.channel)
        )
        ## Check if the recipe is in ggd
        ggd_jsonDict = check_ggd_recipe(pkg, args.channel)
        if ggd_jsonDict == None:
            sys.exit()

        ## Check if the recipe is already installed
        if check_if_installed(pkg, ggd_jsonDict, conda_prefix) == False:
            install_list.append(pkg)
        else:
            continue

        ## Check if conda has it installed on the system
        check_conda_installation(pkg, conda_prefix)

    ## Identify any non_cached packages
    cached = []
    non_cached = []
    for pkg in install_list:
        ## Check S3 bucket if version has not been set
        if check_S3_bucket(pkg, ggd_jsonDict):
            cached.append(pkg)

        else:
            non_cached.append(pkg)

    ## If there is a non-cached recipe, set all recipes to non-cahced (Controll for install errors)
    ### This won't happen very often  (Most if not all packages are cached)
    if non_cached:
        non_cached.extend(cached)
        cached = []

    ## Set source environment prefix as an environment variable
    os.environ["CONDA_SOURCE_PREFIX"] = conda_root()

    ## Install
    if cached:
        print(
            "\n\n:ggd:install:   Attempting to install the following cached package(s):\n\t{}\n".format(
                "\n\t".join(cached)
            )
        )
        install_from_cached(
            cached, args.channel, ggd_jsonDict, debug=args.debug, prefix=conda_prefix
        )

    if non_cached:
        print(
            "\n\n:ggd:install:   Attempting to install the following non-cached package(s):\n\t{}\n".format(
                "\n\t".join(non_cached)
            )
        )
        conda_install(
            non_cached,
            args.channel,
            ggd_jsonDict,
            debug=args.debug,
            prefix=conda_prefix,
        )

    ## If something is installed, shoe the installed pkg info
    if install_list:
        ## List Installed Packages
        get_file_locations(pkg_list, ggd_jsonDict, conda_prefix)

        ## Show environment variables if prefix is current environment
        if conda_prefix == None or os.path.normpath(conda_prefix) == os.path.normpath(
            conda_root()
        ):
            from .show_env import activate_enviroment_variables

            print("\n:ggd:install: Environment Variables")
            activate_enviroment_variables()

    print("\n:ggd:install: DONE")

    return True
