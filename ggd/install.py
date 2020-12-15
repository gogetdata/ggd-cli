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

from .utils import check_for_meta_recipes, conda_root, extract_metarecipe_recipe_from_bz2, get_ggd_channels, get_meta_recipe_pkg, get_repodata 

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
        help="(Optional) The name or the full directory path to an existing conda environment where you want to install a ggd data package. (Only needed if you want to install the data package into a different conda environment then the one you are currently in)",
    )
    c.add_argument(
        "--id",
        metavar="Meta-recipe ID",
        help = ("The ID to use for the meta recipe being installed. For example, if installing the GEO meta-recipe for GEO Accession ID GSE123, use `--id GSE123`"
                " NOTE: GGD will NOT try to correcet the ID. The ID must be accurately entered with case sensitive alphanumeric order") 
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
     the installation proceeds. If not, the installation stops

    Parameters:
    ----------
    1) ggd_recipe:  (str) The name of a ggd-recipe:
    2) ggd_channel: (str) The name of a ggd channel (specific for metadata)

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
    1) ggd_recipe: (list) The name of a recipe to check if it is installed or not
    2) ggd_jdict:  (dict) The channel specific metadata file as a dictionary 
    3) prefix:     (str)  The prefix/conda environment to check in
    
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
    1) ggd_recipe: (str) The name of a ggd package to check if it has been installed by conda
    2) prefix:     (str) The conda environment/prefix to check in

    Returns:
    ++++++++
    1) False if it has not been installed
    2) sys.exit() if it has been installed. (Which means it hasn't been installed by ggd and needs to be uninstalled before
           proceeding)
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
            ":ggd:install:\t To re-install run:\n\t\t $ ggd uninstall %s \n\t\t $ ggd install %s"
            % (ggd_recipe, ggd_recipe)
        )
        if prefix != conda_root():
            print(
                ":ggd:install:\t NOTE: You must activate the conda prefix {p} before running the uninstall command".format(
                    p=target_prefix
                )
            )
        sys.exit()


def get_idname_from_metarecipe(accession_id, meta_recipe_name, jdict):
    """
    get_idname_from_metarecipe
    ===========================
    Get the new name based on an accession id for a recipe to be installed from a meta-recipe 

    Paramters:
    ----------
    1) accession_id:     (str)  The meta-recipe id for the new name 
    2) meta_recipe_name: (str)  The name of the meta recipe which is used to install the new recipe
    3) jdict:            (dict) The channeldata metadata json file loaded as a dict. (Channel == the channel 
                                 the meta recipe is in)
    Returns:
    ++++++++
    1) The id sepecific recipe name from the meta recipe
    """

    new_recipe_name = "{}-{}-v{}".format(accession_id, 
                                         jdict["packages"][meta_recipe_name]["tags"]["data-provider"].lower(), 
                                         jdict["packages"][meta_recipe_name]["version"])
    return(new_recipe_name)


def check_S3_bucket(ggd_recipe, ggd_jdict):
    """Method to check if the recipe is stored on the ggd S3 bucket. If so it installs from S3

    check_S3_bucket
    ==============
    This method is used to check if the recipe has been cached on aws S3 bucket. It returns true if the 
     the recipe is cached, and false if it is not. If it is cached the cached version will be installed. 

    Parameters:
    -----------
    1) ggd_recipe: (str)  The name of a recipe to check if it is installed or not
    2) ggd_jdict:  (dict) The channel specific metadata file as a dictionary 

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
    1) ggd_recipes: (list) A list of ggd recipes that are cached to install
    2) ggd_channel: (str)  The ggd channel for the recipes
    3) ggd_jdict:   (dict) The metadata json dictionary for the ggd recipes
    4) debug:       (bool) Whether to show debug output or not
    5) prefix:      (str)  The prefix/conda environment to install into

    Returns:
    +++++++
    True if successful install
    """
    from .utils import (
        ChecksumError,
        bypass_satsolver_on_install,
        update_installed_pkg_metadata,
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


def conda_install(ggd_recipes, ggd_channel, ggd_jdict, debug=False, prefix=None,  meta_recipe = False, meta_recipe_name = None):
    """Method to install the recipe from the ggd-channel using conda
    
    conda_install
    ============
    This method is used to install the ggd recipe from the ggd conda channel using conda, if the files 
     have not been cached. 

    Parameters:
    ----------
    1) ggd_recipes:      (list) A list of ggd recipes that are cached to install
    2) ggd_channel:      (str)  The ggd channel for the recipes
    3) ggd_jdict:        (dict) The metadata json dictionary for the ggd recipes
    4) debug:            (bool) Whether to show debug output or not
    5) prefix:           (str)  The prefix/conda environment to install into
    6) meta_recipe:      (bool) Whether or not the recipe being installed is a meta recipe. If it is a meta recipe
                              the pkg needs to be installed from local
    7) meta_recipe_name: (str) The name of the meta recipe if one exists

    Returns:
    +++++++
    True if successful install
    """
    from .utils import (
        ChecksumError,
        get_required_conda_version,
        update_installed_pkg_metadata,
    )

    ## Get the target prefix
    target_prefix = prefix if prefix != None else conda_root()

    ## Get conda version
    conda_version, equals = get_required_conda_version()

    ## create install string
    conda_install_str = "{}conda{}{}{}".format('"', equals, conda_version, '"')

    try:
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

        if meta_recipe:

            ## Update command
            command.append("--use-local")

            ## Set up meta-recipe env var tracking
            from .utils import create_tmp_meta_recipe_env_file
            env_var_tmp_dir, env_var_file_path, final_commands_files = create_tmp_meta_recipe_env_file()
            os.environ["GGD_METARECIPE_ENV_VAR_FILE"] = env_var_file_path
            os.environ["GGD_METARECIPE_FINAL_COMMANDS_FILE"] = final_commands_files

        ## Install 
        sp.check_call(command, stderr=sys.stderr, stdout=sys.stdout)

    except sp.CalledProcessError as e:
        from .uninstall import check_for_installation

        sys.stderr.write(
            "\n:ggd:install: !!ERROR!! in install %s\n" % ", ".join(ggd_recipes)
        )
        sys.stderr.write(str(e))

        sys.stderr.write(
            "\n:ggd:install: Removing files created by ggd during installation"
        )
        check_for_installation(
            ggd_recipes, ggd_jdict, target_prefix
        )  ## .uninstall method to remove extra ggd files
        sys.exit(e.returncode)

    ## If meta-recipe, update metadata
    if meta_recipe:

        try:
            import json

            print("\n:ggd:install: Loading Meta-Recipe ID specific environmnet variables")
            ## Get the updated env var list
            meta_env_vars = json.load(open(env_var_file_path)) if os.path.exists(env_var_file_path) else {}

            ## Get the ID specific commands
            commands_str = "\n".join([x.strip() for x in open(final_commands_files, "r")]) if os.path.exists(final_commands_files) else ""
                
            ## Remove tmp dir
            shutil.rmtree(env_var_tmp_dir)

            ## Get a list of installed files
            pkg_name = ggd_recipes[0]
            species = ggd_jdict["packages"][pkg_name]["identifiers"]["species"]
            build = ggd_jdict["packages"][pkg_name]["identifiers"]["genome-build"]
            version = ggd_jdict["packages"][pkg_name]["version"]
            path = os.path.join(
                target_prefix, "share", "ggd", species, build, pkg_name, version
            )
            recipe_files = os.listdir(path)

            ## Get the file sizes
            from .utils import get_file_size, update_metarecipe_metadata
            from collections import defaultdict
            file_size_dict = defaultdict(str)
            for f in recipe_files:
                fsize, tsize, bsize = get_file_size(os.path.join(path,f))
                file_size_dict[f] = fsize

            ## Update meta-recipe meatada 
            success, new_bz2 = update_metarecipe_metadata(pkg_name = pkg_name,
                                                         env_var_dict = meta_env_vars,
                                                         parent_name = meta_recipe_name,
                                                         final_file_list = recipe_files,
                                                         final_file_size_dict = dict(file_size_dict),
                                                         commands_str = commands_str,
                                                         prefix = target_prefix)
            
            assert success, "\n:ggd:install: !!ERROR!! There was a problem updating the meta-recipe metadata"

        except Exception as e:
            from .uninstall import check_for_installation
            import traceback
            print("\n:ggd:install: !!ERROR!! Post-Installation problems while updaing meta-recipe metadata")
            print(str(e))
            print(traceback.print_exc())
            check_for_installation(
                ggd_recipes, ggd_jdict, target_prefix
            )  ## .uninstall method to remove extra ggd files
            sys.exit(1)


    ## copy tarball and pkg file to target prefix
    if prefix != None and prefix != conda_root():
        copy_pkg_files_to_prefix(prefix, ggd_recipes, meta_recipe)

    ## Update installed metadata
    print("\n:ggd:install: Updating installed package list")
    update_installed_pkg_metadata(
        prefix=target_prefix, remove_old=False, add_packages=ggd_recipes, include_local = True if meta_recipe else False
    )

    ## Checkusm
    try:
        install_checksum(ggd_recipes, ggd_jdict, target_prefix, meta_recipe, meta_recipe_name)
    except ChecksumError as e:
        from .uninstall import check_for_installation

        sys.stderr.write(
            "\n:ggd:install: !!ERROR!! in install %s\n" % ", ".join(ggd_recipes)
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
    1) ggd_recipes: (list) A list of ggd package names to install
    2) ggd_jdict:   (dict) ggd channel metadata as a dictionary 
    3) prefix:      (str)  The conda prefix/environment the packages are being installed into
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
            print("\n:ggd:install: There was an error during installation")
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
        ":ggd:install: To activate environment variables run `source activate base` in the environment the packages were installed in\n"
    )
    if prefix != None:
        print(
            ":ggd:install: NOTE: These environment variables are specific to the %s conda environment and can only be accessed from within that environment"
            % prefix
        )
    print(
        "======================================================================================================================"
    )
    print("\n\n")


def install_checksum(pkg_names, ggd_jdict, prefix=conda_root(), meta_recipe = False, meta_recipe_name = ""):
    """Method to check the md5sums of the installed files against the metadata md5sums

    install_checksum
    ================
    This method is used to run checksum on the installed files to make sure the contents of data files 
     was downloaded correctly 
    
    Parameters:
    -----------
    1) pkg_names:        (list) A list of the package names that were installed
    2) ggd_jdict:        (dict) ggd channel metadata as a dictionary 
    3) prefix:           (str)  The prefix the packages were installed into
    4) meta_recipe:      (bool) Whether or not the pkg is a meta-recipe or not
    8) meta_recipe_name: (str)  The name of the meta recipe if one exists

    Returns:
    +++++++
    1) True if checksum passes
    2) raises "ChecksumError" if fails
    """
    import tarfile

    from .utils import (
        ChecksumError,
        data_file_checksum,
        get_checksum_dict_from_tar,
        get_conda_package_list,
        get_meta_recipe_checksum,
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
        if meta_recipe:
            print("\n:ggd:install: NOTICE: Skipping checkusm for meta-recipe {} => {}".format(meta_recipe_name, ", ".join(pkg_names)))
            checksum_dict = {}
#            try:
#                checksum_dict = get_meta_recipe_checksum(meta_recipe_name, pkg_name) 
#            except SystemExit as e:
#                print(str(e))
#                raise ChecksumError(pkg_name)
        else:
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
                    "\n:ggd:install: !!ERROR!! There was an error during the installation of {} and the files weren't installed correctly".format(
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


def copy_pkg_files_to_prefix(prefix, pkg_names, meta_recipe = False):
    """Method to copy the tar and package files from the current conda envrionment to the target prefix
    
    copy_pkg_files_to_prefix
    ========================
    This method is used to copy the tarball file and the pkg file from the current conda envrionment to the 
     target prefix if the prefix flag is set. This will support pkg info lookup for data management when installing
     a package using the prefix flag

    Parameters:
    -----------
    1) prefix:      (str)  The user set prefix 
    2) pkg_names:   (str)  A list of he names of the packages being installed
    3) meta_recipe: (bool) Whether or not the recipe is a meta-recipe

    Returns:
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

    data_packages = get_conda_package_list(prefix, include_local = True if meta_recipe else False)
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
    and file handling. 
    """

    ## If no package names are provided and no file is given, exit
    if not args.name and not args.file:
        sys.exit(
            "\n\n:ggd:install: !!ERROR!! Either a data package name or a file name with --file is required. Neither option was provided.\n"
        )

    ## Check the prefix is a real one
    from .utils import get_conda_prefix_path, prefix_in_conda

    diff_prefix = False
    if args.prefix != None:
        prefix_in_conda(args.prefix)
        diff_prefix = True
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

    pkg_list = list(filter(None, pkg_list))

    ## Check each package
    install_list = []
    is_metarecipe = False
    metarecipe_name = ""
    for pkg in sorted(pkg_list):
        print(
            "\n\n:ggd:install: Looking for %s in the 'ggd-%s' channel"
            % (pkg, args.channel)
        )
        ## Check if the recipe is in ggd
        ggd_jsonDict = check_ggd_recipe(pkg, args.channel)
        if ggd_jsonDict == None:
            sys.exit()

        ## Check if pkg is a meta-recipe 
        if check_for_meta_recipes(name = pkg, jdict = ggd_jsonDict):

            print("\n:ggd:install: {} is a meta-recipe. Checking meta-recipe for installation".format(pkg))
            is_metarecipe = True
            metarecipe_name = pkg

            ## Check number of packages
            if len(pkg_list) > 1:
                print("\n:ggd:install: GGD is currenlty only able to install a single meta-recipe at a time. Please remove other pkgs and install them with a subsequent command")
                sys.exit()

            ## Check for an meta-recipe ID 
            if not args.id:
                print("\n:ggd:install: An ID is required in order to install a GGD meta-recipe. Please add the '--id <Some ID>' flag and try again")
                sys.exit()

            ## Id must be lower case for conda
            meta_recipe_id = args.id.lower()

            ## Get the new name
            new_recipe_name = get_idname_from_metarecipe(meta_recipe_id, pkg, ggd_jsonDict)
            print("\n:ggd:install: The ID specific recipe to be installed is '{}'.".format(new_recipe_name))

            ## update the meta data dict with the new recipe 
            ggd_jsonDict["packages"][new_recipe_name] = ggd_jsonDict["packages"][pkg]

            ## Check if already installed
            if check_if_installed(new_recipe_name, ggd_jsonDict, conda_prefix):
                continue

            ## Download the meta recipe pkg
            try:
                prefix_pkg_dir, tarball_name, tarball_path = get_meta_recipe_pkg(pkg, ggd_jsonDict, args.channel, conda_prefix)
            except AssertionError as e:
                print("\n:ggd:install: !!ERROR!! There was a problem during the installation of the the meta-recipe pkg file")
                print(str(e))
                sys.exit(1)
                
            ## Create the new id specific recipe from the meta-recipe
            success, new_recipe_path, tmpdir = extract_metarecipe_recipe_from_bz2(pkg, new_recipe_name, tarball_path)

            ## Check for success
            try:
                assert (success), "\n:ggd:install: !!ERROR!! There was a problem updating the meta-recipe to the ID speciifc recipe"
            except AssertionError as e:
                print(str(e))
                if tmpdir:
                    shutil.rmtree(tmpdir)
                sys.exit(1)

            ## Open the new recipe yaml file
            import yaml
            try:
                recipe_yaml = yaml.safe_load(open(os.path.join(new_recipe_path, "meta.yaml")))
            except Exception as e:
                print("\n:ggd:install: !!ERROR!! Unable to read the new recipe yaml file")
                print(str(e))
                if tmpdir:
                    shutil.rmtree(tmpdir)
                sys.exit(1)

            ## Build the tar.bz2 file for the new recipe
            print("\n:ggd:install: Building new ID specific pkg\n")
            from .check_recipe import _build
            try:
                new_bz2 = _build(new_recipe_path, recipe_yaml, debug = True if args.debug else False)
                assert (os.path.exists(new_bz2)), "\n:ggd:install: !!ERRORR!! There was a problem building the new recipe"
            except Exception as e:
                print(str(e))
                if tmpdir:
                    shutil.rmtree(tmpdir)
                sys.exit(1)

            print("\n:ggd:install: Successfully built new ID specific meta recipe")
            
            ## Remove the tmpdir
            if tmpdir:
                shutil.rmtree(tmpdir)

            ## Update pkg name to the new recipe name
            pkg = new_recipe_name
            pkg_list = [pkg]

            ## Set the GGD meta-recipe environment variable
            os.environ["GGD_METARECIPE_ID"] = args.id

        ## Check that the package is set up for installation into a different prefix if one is provided
        if diff_prefix and conda_prefix != conda_root():
            assert "final-files" in ggd_jsonDict["packages"][pkg]["tags"], (
                "\n\n:ggd:install: !!ERROR!! the --prefix flag was set but the '{}' data package is not set up"
                " to be installed into a different prefix. GGD is unable to fulfill the install request. Remove the"
                " --prefix flag to install this data package. Notify the ggd team if you would like this recipe"
                " to be updated for --prefix install compatibility"
            ).format(pkg)

        ## Check if the recipe is already installed
        if check_if_installed(pkg, ggd_jsonDict, conda_prefix) == False:
            install_list.append(pkg)
        else:
            continue

        ## Check if conda has it installed on the system
        check_conda_installation(pkg, conda_prefix)

    ## Provide a warning if the id parameter was set but no meta-recipes are being installed
    if not is_metarecipe and args.id:
        print("\n:ggd:install: WARNING: The '--id' argument was set but no meta-recipes are being installed. ID {} will not be used".format(args.id))

    ## Identify any non_cached packages
    cached = []
    non_cached = []
    for pkg in install_list:
        ## Check S3 bucket if version has not been set
        if check_S3_bucket(pkg, ggd_jsonDict):
            cached.append(pkg)

        else:
            non_cached.append(pkg)

    ## If there is a non-cached recipe, set all recipes to non-cached (Control for install errors)
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
            meta_recipe = is_metarecipe,
            meta_recipe_name = metarecipe_name
        )

    ## If something is installed, show the installed pkg info
    if install_list:
        ## List Installed Packages
        get_file_locations(pkg_list, ggd_jsonDict, conda_prefix)

        ## Show environment variables if prefix is current environment
        if conda_prefix == None or os.path.normpath(conda_prefix) == os.path.normpath(
            conda_root()
        ):
            from .show_env import activate_environment_variables

            print("\n:ggd:install: Environment Variables")
            activate_environment_variables()

    print("\n:ggd:install: DONE")

    return True
