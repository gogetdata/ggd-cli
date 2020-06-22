from __future__ import print_function

import os
import os.path as op
import re
import subprocess as sp
import sys

import yaml

from .uninstall import check_for_installation
from .utils import check_output, conda_root

# ---------------------------------------------------------------------------------------------------
# urlib setup based on system version
# ---------------------------------------------------------------------------------------------------
if sys.version_info[0] < 3:
    import urllib

    urlopen = urllib.urlopen
else:
    from urllib.request import urlopen

# ---------------------------------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------------------------------


def add_check_recipe(p):
    """Argument method used to add check-recipe as a module arugment/function """
    import argparse

    c = p.add_parser(
        "check-recipe",
        help="Build, install, check, and test a ggd data recipe",
        description="Convert a ggd recipe created from `ggd make-recipe` into a data package. Test both ggd data recipe and data package",
    )
    c.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="(Optional) Set the stdout log level to debug",
    )
    c.add_argument(
        "-du",
        "--dont_uninstall",
        action="store_true",
        help='(Optional) By default the newly installed local ggd data package is uninstalled after the check has finished. To bypass this uninstall step (to keep the local package installed) set this flag "--dont_uninstall"',
    )
    c.add_argument(
        "--dont-add-md5sum-for-checksum",
        action="store_true",
        required=False,
        help=argparse.SUPPRESS,
    )
    c.add_argument(
        "recipe_path", help="path to recipe directory (can also be path to the .bz2)"
    )

    c.set_defaults(func=check_recipe)


# ---------------------------------------------------------------------------------------------------
# Functions/methods
# ---------------------------------------------------------------------------------------------------


def list_files(dir):
    """Method to list files in a given directory 

    list_files
    ==========
    This method is used to list all the files in a give directory. If files are 
     present and are not empty they are included in the return list. A list of files 
     in the dir path is returned. 
    """

    rfiles = []
    subdirs = [x[0] for x in os.walk(dir)]
    for subdir in subdirs:
        # files = next(os.walk(subdir))[2]
        files_list = next(os.walk(subdir))
        files = files_list[2]
        if len(files) > 0:
            for file in files:
                rfiles.append(op.join(subdir, file))
    return [(p, os.stat(p).st_mtime) for p in rfiles]


def conda_platform():
    """Method to get the system platform to build and install a ggd package

    conda_platform
    ==============
    This method is used to identify the system platform being used. Building and install a data
     package is dependent on the system platform. (OSX, Linux, etc.) The system platform will
     be returned.
    """

    vs = [x for x in check_output(["conda", "info"]).split("\n") if "platform :" in x]
    assert len(vs) == 1, vs
    return vs[0].split("platform :")[1].strip()


def _build(path, recipe, debug=False):
    """Method used to build a ggd package from a ggd recipe 

    _build
    ======
    This method is used to convert/build a ggd package from an existing ggd recipe. A package
     is what will be stored on the conda clound. This method ensures that the ggd recipe can 
     be properly built into a package.

    Parameters:
    ----------
    1) path: The path to the ggd recipe 
    2) recipe: The meta.yaml from the ggd recipe loaded as a dictionary 

    Returns:
    ++++++++
    1) The absolute path to the bz2 file, the new ggd data package file, created by conda build
    """
    from .install import check_ggd_recipe

    ## Set CONDA_SOURCE_PREFIX environment variable for any ggd dependencies that will be installed during the build 
    os.environ["CONDA_SOURCE_PREFIX"] = conda_root()

    sp.check_call(["conda", "build", "purge"], stderr=sys.stderr, stdout=sys.stdout)
    try:
        if debug:
            out = check_output(
                [
                    "conda",
                    "build",
                    "--debug",
                    "--no-anaconda-upload",
                    "-c",
                    "ggd-genomics",
                    path,
                ],
                stderr=sys.stderr,
            )
        else:
            out = check_output(
                ["conda", "build", "--no-anaconda-upload", "-c", "ggd-genomics", path],
                stderr=sys.stderr,
            )

    except Exception:
        ## Check all requirenments for ggd dependencies
        print(":ggd:check-recipe: Rolling back ggd dependencies")
        for d in recipe["requirements"]["build"]:
            try:
                ggd_jdict = check_ggd_recipe(d, ggd_channel="genomics")
            except SystemExit:
                ggd_jdict = None

            if ggd_jdict != None:
                print(":ggd:check-recipe: Rolling back %s" % d)
                ## Remove ggd files
                check_for_installation(
                    [d], ggd_jdict
                )  ## .uninstall method to remove extra ggd files
        print(
            "\n:ggd:check-recipe: Review the STDOUT and STDERR, correct the errors, and re-run $ggd check-recipe\n"
        )
        ## Exit
        sys.exit(5)

    pattern = "Package:.+"
    result = re.search(pattern, out)
    if result == None:  ## If pattern not found
        pattern = "Packaging.+"
        result = re.findall(pattern, out)

    name = (
        result[-1].split()[1].replace(".tar.bz2", "") + ".tar.bz2"
    )  # name of the file: exapmle = hg19-phastcons-1-0.tar.bz2

    platform = (
        "noarch" if "noarch" in recipe["build"] else conda_platform()
    )  ## Check for noarch platform
    path = op.join(conda_root(), "conda-bld", platform)

    return os.path.join(path, name)


def _install(bz2, recipe_name, debug=False):
    """Method to install a local pre-built package to ensure package installs correctly 

    _install
    ========
    This method is used to install a pre-built ggd package. conda build was used to turn the ggd recipe into a 
     ggd package. This script will take the locally built ggd package and install it. This method is used to 
     ensure the package installs correctly.

    Parameters:
    -----------
    1) bz2: The bz2 tarball package file created from the conda build
    2) recipe_name: The name of the ggd recipe/package

    Returns:
    +++++++
    1) True if the installation was successful and the package was not already installed on the system
    2) False if the package has already been installed on the system
    3) If the installation fails progam exits. ggd data handeling is initated to remove any new/updated files from the installation process
    """
    import traceback
    from .utils import get_conda_package_list, get_required_conda_version

    conda_version, equals = get_required_conda_version()
    conda_install = "\"" + "conda" + equals + conda_version + "\""

    ## See if it is already installed
    if recipe_name in get_conda_package_list(conda_root(),include_local=True).keys():
        return False

    ## Set CONDA_SOURCE_PREFIX environment variable
    os.environ["CONDA_SOURCE_PREFIX"] = conda_root()

    ## Install the new recipe
    try:
        if conda_version != -1:
            if debug:
                sp.check_call(
                    [
                        "conda",
                        "install",
                        "-v",
                        "--use-local",
                        "-y",
                        recipe_name,
                        conda_install,
                        "--debug",
                    ],
                    stderr=sys.stderr,
                    stdout=sys.stdout,
                )
            else:
                sp.check_call(
                    [
                        "conda",
                        "install",
                        "-v",
                        "--use-local",
                        "-y",
                        recipe_name,
                        conda_install,
                    ],
                    stderr=sys.stderr,
                    stdout=sys.stdout,
                )
        else:
            if debug:
                sp.check_call(
                    [
                        "conda",
                        "install",
                        "-v",
                        "--use-local",
                        "-y",
                        recipe_name,
                        "--debug",
                    ],
                    stderr=sys.stderr,
                    stdout=sys.stdout,
                )
            else:
                sp.check_call(
                    ["conda", "install", "-v", "--use-local", "-y", recipe_name],
                    stderr=sys.stderr,
                    stdout=sys.stdout,
                )

    except Exception as e:
        print(e)
        print(
            "\n:ggd:check-recipe: %s did not install properly. \n\n\t->Error message:\n"
            % recipe_name
        )
        print(traceback.format_exc())

        ## Remove ggd files
        recipe_dict = get_recipe_from_bz2(bz2)
        species = recipe_dict["about"]["identifiers"]["species"]
        genome_build = recipe_dict["about"]["identifiers"]["genome-build"]
        version = recipe_dict["package"]["version"]
        name = recipe_dict["package"]["name"]
        ggd_jdict = {
            "packages": {
                name: {
                    "identifiers": {"species": species, "genome-build": genome_build},
                    "version": version,
                }
            }
        }
        try:
            check_for_installation(
                [recipe_name], ggd_jdict
            )  ## .uninstall method to remove extra ggd files
        except Exception as e:
            print(e)

        print(
            "\n:ggd:check-recipe: Review the STDOUT and STDERR, correct the errors, and re-run $ggd check-recipe\n"
        )
        ## Exit
        sys.exit(1)

    return True


def get_recipe_from_bz2(fbz2):
    """Method used to get the meta.yaml file from a ggd package that has been built and is in a bz2 file format

    get_recipe_from_bz2
    ===================
    This method is used to obtain a ggd recipe's meta.yaml file from an already built ggd package. It extracts 
    the bz2 tarball file and identifies the meta,yaml file. 

    Parameters:
    ----------
    1) fbz2: The file path to the pre-built bz2 ggd package
    
    Return:
    +++++++
    1) The meta.yaml file as a dictionary 
    """
    import tarfile

    info = None
    with tarfile.open(fbz2, mode="r|bz2") as tf:
        for info in tf:
            # this was changed recently in conda/conda-build
            if info.name in ("info/recipe/meta.yaml", "info/meta.yaml"):
                break
        else:
            print(
                ":ggd:check-recipe: !!ERROR!!: Incorrect tar.bz format.",
                file=sys.stderr,
            )
            exit(1)
        recipe = tf.extractfile(info)
        recipe = yaml.safe_load(recipe.read().decode())
    return recipe


def _check_build(species, build):
    """Method to check the genome-build is one available and correct in GGD. 

    _check_build
    ============
    Checks the supplied genome build with the available genome builds in GGD.

    Parameters:
    -----------
    1) species: The supplied species for the recipe being built
    2) build: The genome build for the recipe being built

    Returns:
    ++++++++
    1) True if gnome build is correct, raises an error otherwise 

    """
    from .utils import check_for_internet_connection, get_species

    if check_for_internet_connection():
        gf = "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/{species}/{build}/{build}.genome".format(
            build=build, species=species
        )
        try:
            ret = urlopen(gf)
            if ret.getcode() >= 400:
                raise Exception("%s at url: %s" % (ret.getcode(), gf))
        except:
            sys.stderr.write(
                "ERROR: genome-build: %s not found in github repo for the %s species.\n"
                % (build, species)
            )
            raise
        return True
    else:  ## If no internet conection (mostly for make-recipe in an internet free context)
        ## Get a dictionary with keys as species and values as genome builds
        species_build_dict = get_species(full_dict=True)
        if build in species_build_dict[species]:
            return True
        else:
            sys.stderr.write(
                "ERROR: genome-build: %s not found in github repo for the %s species.\n"
                % (build, species)
            )
            raise


def check_recipe(parser, args):
    """Main method to check a ggd recipe for proper filing, system handeling, package building, install, etc. 

    check_recipe
    ============
    The main function for the ggd check-recipe module. This function controls the different checks, builds, and installs.
    """

    if args.recipe_path.endswith(".bz2"):
        recipe = get_recipe_from_bz2(args.recipe_path)
        bz2 = args.recipe_path
        args.dont_add_md5sum_for_checksum = True  ## If bz2, final files should have already beed added and checksum should have already been calculated.
    else:
        recipe = yaml.safe_load(open(op.join(args.recipe_path, "meta.yaml")))
        if args.debug:
            bz2 = _build(args.recipe_path, recipe, debug=True)
        else:
            bz2 = _build(args.recipe_path, recipe)

    ## If skipping md5sum and final file creation, check the yaml file
    if args.dont_add_md5sum_for_checksum:
        assert (
            len(recipe["about"]["tags"].get("final-files", [])) > 0
        ), ":ggd:check-recipe: final-files are missing from the meta.yaml file and is required if md5sum is being skipped. Please run 'ggd check-recipe <recipe>' with the NON tar.bz2 recipe and WITHOUT the --dont-add-md5sum-for-checksum flag set"
        assert (
            len(recipe["about"]["tags"].get("file-type", [])) > 0
        ), ":ggd:check-recipe: file-type is missing from the meta.yaml file and is required if md5sum is being skipped. Please run 'ggd check-recipe <recipe>' with the NON tar.bz2 recipe and WITHOUT the --dont-add-md5sum-for-checksum flag set"

    species, build, version, recipe_name = check_yaml(recipe)

    _check_build(species, build)

    install_path = op.join(
        conda_root(), "share", "ggd", species, build, recipe_name, version
    )

    before = list_files(install_path)

    if args.debug:
        new_installed = _install(bz2, str(recipe["package"]["name"]), debug=True)
    else:
        new_installed = _install(bz2, str(recipe["package"]["name"]))

    ## Check if previous package is already installed or it is a new installation
    if new_installed:

        ## Check that the file has a header
        if not check_header(install_path):
            print("\n:ggd:check-recipe: !!ERROR!!")
            print(
                "\n\t!!!!!!!!!!!!!!!!!!!!!!!\n\t! FAILED recipe check !\n\t!!!!!!!!!!!!!!!!!!!!!!!\n"
            )
            print(
                "\n\t!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\t! Recipe NOT ready for Pull Requests !\n\t!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            )
            remove_package_after_install(bz2, recipe_name, 1)
            
        ## Get the extra files
        extra = check_files(
            install_path,
            species,
            build,
            recipe["package"]["name"],
            recipe["extra"].get("extra-files", []),
            before,
            bz2,
        )

        ## Add final files and md5sum
        if args.dont_add_md5sum_for_checksum == False:
            recipe = add_final_files(install_path, recipe, args.recipe_path, extra)
            add_to_checksum_md5sums(
                install_path, recipe, op.join(args.recipe_path, "checksums_file.txt")
            )

            print(
                "\n\t****************************\n\t* Successful recipe check! *\n\t****************************\n"
            )
            print(
                "\n\t**********************************\n\t* Recipe ready for Pull Requests *\n\t**********************************\n"
            )

        ## If skipping md5sum addition, check md5sum for each file
        else:
            ## Check final installed data files
            try:
                check_final_files(install_path, recipe)
            except AssertionError as e:
                print("\n:ggd:check-recipe: !!ERROR!!", str(e))
                print(
                    "\n\t!!!!!!!!!!!!!!!!!!!!!!!\n\t! FAILED recipe check !\n\t!!!!!!!!!!!!!!!!!!!!!!!\n"
                )
                print(
                    "\n\t!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\t! Recipe NOT ready for Pull Requests !\n\t!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
                )
                remove_package_after_install(bz2, recipe_name, 111)

            ## Check that the checksum in the .bz2 file has a filled checksum file
            from .utils import get_checksum_dict_from_tar, data_file_checksum

            checksum_dict = get_checksum_dict_from_tar(bz2)
            if not data_file_checksum(install_path, checksum_dict):
                print(
                    "\n\t!!!!!!!!!!!!!!!!!!!!!!!\n\t! FAILED recipe check !\n\t!!!!!!!!!!!!!!!!!!!!!!!\n"
                )
                print(
                    "\n\t!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\t! Recipe NOT ready for Pull Requests !\n\t!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
                )
                remove_package_after_install(bz2, recipe_name, 222)

            else:
                print(
                    "\n\t****************************\n\t* Successful recipe check! *\n\t****************************\n"
                )
                print(
                    "\n\t**********************************\n\t* Recipe ready for Pull Requests *\n\t**********************************\n"
                )

    else:  ## if already installed
        print("\n:ggd:check-recipe: Package already installed on your system")
        print(
            '\nggd:check-recipe: If the "-du" flag (dont_uninstall) is NOT set this package will be uninstalled'
        )
        print("\n:ggd:check-recipe: To recheck this recipe")
        if args.dont_uninstall == True:
            print(
                ' 1) Uninstall the reicpe with: \n\t$ ggd check-recipe {} \tNOTE: Make sure the "-du" flag is NOT set'.format(
                    args.recipe_path
                )
            )
            print(
                ' 2) Run check recipes again once the local package is uninstalled (From step 1): \n\t $ggd check-recipe {} \tNOTE: With or without the "-du" flag.'.format(
                    args.recipe_path
                )
            )
        else:
            print(
                ' 1) Run check recipes again once the local package is uninstalled: \n\t $ggd check-recipe {} \tNOTE: With or without the "-du" flag.'.format(
                    args.recipe_path
                )
            )

    if args.dont_uninstall == False:
        print(
            "\n\n:ggd:check-recipe: The --dont_uninstall flag was not set \n\n Uninstalling the locally built ggd data package"
        )

        recipe_dict = get_recipe_from_bz2(bz2)
        species = recipe_dict["about"]["identifiers"]["species"]
        genome_build = recipe_dict["about"]["identifiers"]["genome-build"]
        version = recipe_dict["package"]["version"]
        name = recipe_dict["package"]["name"]
        ggd_jdict = {
            "packages": {
                name: {
                    "identifiers": {"species": species, "genome-build": genome_build},
                    "version": version,
                }
            }
        }
        try:
            check_for_installation(
                [name], ggd_jdict
            )  ## .uninstall method to remove extra ggd files
        except Exception as e:
            print(e)
    else:
        recipe_dict = get_recipe_from_bz2(bz2)
        name = recipe_dict["package"]["name"]
        print(
            "\n\n:ggd:check-recipe: {} will remain installed on your system as a local data package.".format(
                name
            )
        )

    return True


def add_to_checksum_md5sums(installed_dir_path, yaml_file, recipe_checksum_file_path):
    """Method to add/update md5sums for each final file in a recipe for checksum 

    add_to_checksum_md5sums
    =======================
    Method to update the checksum_file.txt file for the current recipe. This method will
     add an entry in the checksum file for each processed/final file in the recipe.

    Parameters:
    -----------
    1) installed_dir_path: The directory path to the installed data files, excluding the version number
    2) yaml_file: The meta.yaml file for the recipe
    3) recipe_checksum_file_path: The file path to the checksum recipe to update

    Returns:
    ++++++++
    1) Nothing is returned. The checksum file is updated with each data file and it's md5sum.
        Each data file will be placed on its own line with a tab seperating the file's md5sum.
    """
    print(":ggd:check-recipe: Updating md5sums for final data files\n")
    import glob
    from .utils import get_file_md5sum

    with open(recipe_checksum_file_path, "w") as cs_file:
        installed_files = glob.glob(op.join(installed_dir_path, "*"))

        ## Check the number of files are the same between the yaml file and the acutal data files
        final_files = yaml_file["about"]["tags"]["final-files"]
        assert len(final_files) == len(installed_files), (
            ":ggd:check-recipe: The number of installed files does not match the number of final files listed in the recipe."
            + " Number of installed files = {i}, Number of final files in recipe = {f}".format(
                i=len(installed_files), f=len(final_files)
            )
        )

        for ifile in installed_files:
            cs_file.write(op.basename(ifile) + "\t" + get_file_md5sum(ifile) + "\n")

    return True


def add_final_files(installed_dir_path, yaml_dict, recipe_path, extra_files):
    """Method to add the final data files to the meta.yaml file of a recipe

    add_final_files
    ===============
    Method to iterate through and add each of the final data files from the processed data package to 
     the meta.yaml file of the checked recipe. (This should be called after the "check_files" function
     has passed.) 
    The file types will be added as well. If they are common genomic file types, otherwise the 
     file extension will be used.
    The meta.yaml file will be re-written with the new file types and final files. 
    New meta.yaml fields = 
        - final-files
        - file-type
        - final-file-sizes

    Parameters:
    -----------
    1) installed_dir_path: The directory path to the installed data files
    2) yaml_dict: A dictionary of the meta.yaml file for the recipe
    3) recipe_path: The directory path to the recipe being checked 
    4) extra_files: The name of the extra files found from check_files method

    Returns: 
    ++++++++
    The yaml dictionary of the new yaml file
    """
    print("\n:ggd:check-recipe: Updating the list of final data files\n")
    import glob
    from .utils import get_file_size

    file_types = set(
        [
            "fasta",
            "fa",
            "fastq",
            "fq",
            "sam",
            "bam",
            "cram",
            "vcf",
            "bcf",
            "bed",
            "bigwig",
            "bw",
            "gff",
            "gtf",
            "gff3",
            "psl",
            "hal",
            "maf",
            "wig",
            "2bit",
            "nib",
            "sff",
            "srf",
            "txt",
            "json",
            "xml",
            "yaml",
            "yml",
            "mzml",
            "cvs",
            "tsv",
            "txt",
            "bim",
            "fam",
            "ped",
            "genome",
        ]
    )

    installed_files = glob.glob(op.join(installed_dir_path, "*"))

    yaml_dict["about"]["tags"]["final-files"] = []
    final_file_types = set()
    file_size_dict = dict()

    ## Add final data files to yaml dict
    for ffile_path in installed_files:

        ## Get the Final File
        ffile = os.path.basename(ffile_path)
        yaml_dict["about"]["tags"]["final-files"].append(ffile)

        ## Get the size of the final file
        file_size = get_file_size(ffile_path)
        file_size_dict[ffile] = file_size

        ## the file type of the final file 
        ftype = [x for x in file_types if x in ffile.lower().split(".")]
        if ftype:
            final_file_types.update(ftype)
        else:
            final_file_types.update([".".join(ffile.split(".")[1:])])

    ## Create a file-type key in the yaml
    yaml_dict["about"]["tags"]["file-type"] = sorted(list(final_file_types))

    ## Add file sizes
    yaml_dict["about"]["tags"]["final-file-sizes"] = file_size_dict

    ## Sort final files
    yaml_dict["about"]["tags"]["final-files"] = sorted(
        yaml_dict["about"]["tags"]["final-files"]
    )

    ## Add extra files if they exists
    if extra_files:
        print(":ggd:check-recipe: Attempting to add the extra files not already added in the meta.yaml file\n")
        yaml_dict["extra"]["extra-files"] = extra_files

    ## Rewrite yaml file with new tags and new final files
    with open(os.path.join(recipe_path, "meta.yaml"), "w") as newFile:
        for key in sorted(yaml_dict.keys()):
            if key != "about":  ## Skip about key for now
                newFile.write(
                    yaml.dump({key: yaml_dict[key]}, default_flow_style=False)
                )
        ## Add in the "about" key
        newFile.write(
            yaml.dump({"about": yaml_dict["about"]}, default_flow_style=False)
        )

    ## Return the new version of the meta.yaml as a dict
    return yaml.safe_load(open(os.path.join(recipe_path, "meta.yaml")))


def check_final_files(installed_dir_path, yaml_file):
    """Method to check the installed files match the files listed in the yaml file

    check_final_files
    =================
    Method to check that the final installed files from the data recipe are the same files listed in the meta.yaml file

    Parameters:
    -----------
    1) installed_dir_path: The directory path to the installed files
    2) yaml_file: The meta.yaml file for the recipe

    Returns:
    ++++++++
    1) True if all passes fail, otherwise an assertion error is raised
    """
    print(":ggd:check-recipe: Checking the final data files\n")
    import glob

    installed_files = glob.glob(op.join(installed_dir_path, "*"))

    final_files = yaml_file["about"]["tags"]["final-files"]

    ## Check that there are the same number of files as files installed.
    assert len(final_files) == len(installed_files), (
        ":ggd:check-recipe: The number of installed files does not match the number of final files listed in the recipe."
        + " Number of installed files = {i}, Number of final files in recipe = {f}".format(
            i=len(installed_files), f=len(final_files)
        )
    )

    ## Test the file exists
    for ffile in final_files:
        ffile_path = op.join(installed_dir_path, ffile)
        assert (
            ffile_path in installed_files
        ), ":ggd:check-recipe: The {ff} file designated in the recipe is not one of the installed files".format(
            ff=ffile
        )
        assert os.path.exists(
            ffile_path
        ), ":ggd:check-recipe: The {ff} file designated in the recipes does not exists as an installed file".format(
            ff=ffile
        )
        assert os.path.isfile(
            ffile_path
        ), ":ggd:check-recipe: The {ff} file designated in the recipes is not a file in the installed path".format(
            ff=ffile
        )

    return True


def get_modified_files(files, before_files):
    """Method to check if the files installed during the installation process of a ggd packages are been modified """

    before_files = dict(before_files)
    files = [p for p, mtime in files if mtime != before_files.get(p, 0)]
    return files


def remove_package_after_install(bz2, recipe_name, exit_num):
    """Method to remove a locally installed ggd package if the post installation checks fail

    remove_package_after_install
    ============================
    Method to uninstall and remove data package files if the post installation steps fail. 
    
    Parameters:
    -----------
    1) bz2: The bz2 file created during the conda build process of the data package
    2) exit_num: The exit number to exit the program with
    """

    print(
        "\n:ggd:check-recipe: !!ERROR!! Post-installation checks have failed. Rolling back installation"
    )

    recipe_dict = get_recipe_from_bz2(bz2)
    species = recipe_dict["about"]["identifiers"]["species"]
    genome_build = recipe_dict["about"]["identifiers"]["genome-build"]
    version = recipe_dict["package"]["version"]
    name = recipe_dict["package"]["name"]
    ggd_jdict = {
        "packages": {
            name: {
                "identifiers": {"species": species, "genome-build": genome_build},
                "version": version,
            }
        }
    }
    try:
        check_for_installation(
            [recipe_name], ggd_jdict
        )  ## .uninstall method to remove extra ggd files
    except Exception as e:
        print(e)

    print(
        "\n:ggd:check-recipe: Review the STDOUT and STDERR, correct the errors, and re-run $ggd check-recipe\n"
    )
    ## Exit
    sys.exit(exit_num)


def check_header(install_path):
    """Method to check the final genomic headers have a header or not

    check_header
    ============
    This method is going to go through each of the files that were created by the recipe, 
     and it will check if the those files have a header or not. 
    
    sam/bam/cram, vcf/bcf, gtf/gff/gff3, bed/bedGraph, csv, txt files require a header and if no header is provided 
     check-recipe will fail. 
   
    Other files that don't have header will be given a warning. GGD expects most files to have 
      a header. Some files are okay not to have headers, but if a header can be added it should be. 

    For each file, the file header and first 5 lines of the file body will be provided to stdout.

    Parameters:
    -----------
    1) install_path: The path to the directory where the files have been installed into.

    Returns:
    +++++++
    True or False. 
     - True if a header exist or if only a warning was given
     - False if a header does not exists and is required

    """

    print(":ggd:check-recipe: Checking that the final files have headers if appropriate\n")

    installed_files = os.listdir(install_path)

    for file_name in [x for x in installed_files if os.path.isfile(os.path.join(install_path,x))]:

        f_path = os.path.join(install_path, file_name)

        ## Check for an index file
        if file_name.strip().split(".")[-1] in set(["tbi","bai","crai","fai","tar","bz2","bw","csi"]):
            continue 

        ## Skip fasta or fastq files
        if any(x in file_name for x in [".fasta",".fa",".fastq",".fq"]):
            continue

        ## Check for sam/bam/cram files
        if any(x in file_name for x in [".sam",".bam",".cram"]):
            import pysam

            try:
                samfile = pysam.AlignmentFile(f_path, check_sq=False)
                header = samfile.header
                if any(header.lengths):
                    print(":ggd:check-recipe: Header found in file {name}\n".format(name=file_name))
                    print("Head of file:")
                    print("---------------------------")
                    print(str(header).strip())
                    for i,read in enumerate(samfile):
                        print(read)
                        if i >= 4: 
                            break
                    print("---------------------------\n")

                else:
                    print(":ggd:check-recipe: !!ERROR!! No header found for file {name}\n".format(name=file_name))
                    print(":ggd:check-recipe: !!ERROR!! A header is required for sam/bam/cram files\n")
                    return(False)

            except (ValueError, IOError, Exception) as e:
                print(str(e))
                print(":ggd:check-recipe: !!ERROR!! No header found for file {name}\n".format(name=file_name))
                print(":ggd:check-recipe: !!ERROR!! A header is required for sam/bam/cram files\n")
                return(False)

    
        ## Check vcf/bcf files
        elif any(x in file_name for x in [".vcf",".bcf"]): 
            from cyvcf2 import VCF
            try:
                vcffile = VCF(f_path)
                header = str(vcffile.raw_header)

                if header:
                    print(":ggd:check-recipe: Header found in file {name}\n".format(name=file_name))
                    print("Head of file:")
                    print("---------------------------")
                    print(str(header).strip())
                    for i,var in enumerate(vcffile):
                        print(var)
                        if i >= 4: 
                            break
                    print("---------------------------\n")

                else:
                    print(":ggd:check-recipe: !!ERROR!! No header found for file {name}\n".format(name=file_name))
                    print(":ggd:check-recipe: !!ERROR!! A header is required for vcf/bcf files\n")
                    return(False)

            except IOError as e:
                print(str(e))
                print(":ggd:check-recipe: !!ERROR!! No header found for file {name}\n".format(name=file_name))
                print(":ggd:check-recipe: !!ERROR!! A header is required for vcf/bcf files\n")
                return(False)

        ## Check other files
        else:
            import gzip
            try:
                file_handler = gzip.open(f_path) if f_path.endswith(".gz") else open(f_path)
                header = []
                body = []
                try:
                    for line in file_handler:

                        if type(line) != str:
                            line = line.strip().decode("utf-8")

                        if len(line) > 0 and str(line)[0] == "#":

                            header.append(str(line).strip())

                        else:
                            body.append(str(line).strip())

                            if len(body) > 4:
                                break

                except UnicodeDecodeError:
                    print(":ggd:check-recipe: Cannot decode file contents into unicode.\n") 
                    pass


                if header:
                    print(":ggd:check-recipe: Header found in file {name}\n".format(name=file_name))
                    print("Head of file:")
                    print("---------------------------")
                    print("\n".join(header))
                    print("\n".join(body))
                    print("---------------------------\n")
                elif any(x in file_name for x in [".gtf", ".gff", ".gff3", ".bed", ".bedGraph", ".csv", ".txt"]):
                    print(":ggd:check-recipe: !!ERROR!! No header found for file {name}\n".format(name=file_name))
                    print(":ggd:check-recipe: !!ERROR!! A header is required for this type of file\n")
                    print("First 5 lines of file body:")
                    print("---------------------------")
                    print("\n".join(body))
                    print("---------------------------\n")
                    return(False)
                else:
                    print(":ggd:check-recipe: !!WARNING!! No header found for file {name}\n".format(name=file_name))
                    print("First 5 lines of file body:")
                    print("---------------------------")
                    print("\n".join(body))
                    print("---------------------------\n")
                    print(":ggd:check-recipe: !!WARNING!! GGD requires that any file that can have a header should. Please either add a header or if the file cannot have a header move forward.\n")
                    print(":ggd:check-recipe: !!WARNING!! IF you move forwared without adding a header when one should be added, this recipe will be rejected until a header is added.\n")
                    
            except IOError as e:
                print(":ggd:check-recipe: !!ERROR!!")
                print(str(e))
                return False

    return(True)


def check_files(
    install_path, species, build, recipe_name, extra_files, before_files, bz2
):
    """Method to check the presence of correct genomic files """
    from fnmatch import fnmatch

    P = "{species}/{build}:{recipe_name}".format(**locals())

    files = list_files(install_path)
    files = get_modified_files(files, before_files)
    if len(files) == 0:
        sys.stderr.write("ERROR: no modified files in %s\n" % install_path)
        remove_package_after_install(bz2, recipe_name, 2)

    print(":ggd:check-recipe: modified files:\n\t :: %s\n\n" % "\n\t :: ".join(files))

    tbis = [x for x in files if x.endswith(".tbi")]  # all tbi files
    tbis = [x for x in files if x.endswith((".tbi",".csi"))]  # all tbi files

    nons = [x for x in files if not x.endswith((".tbi",".csi"))]  # all non tbi files

    tbxs = [x[:-4] for x in tbis if x[:-4] in nons]  # names of files tabixed

    base_tbx_tbi = [
        x[:-3] for x in tbxs if x[:-3] in nons
    ]  # Name of files that are bgzip and tabix3d

    nons = [x for x in nons if x not in tbxs]  # files not tabixed or tbi
    nons = [x for x in nons if x not in base_tbx_tbi]  # files not tabixed or tbi

    # check for fais?
    fais = [x for x in nons if x.endswith(".fai")]  # all fai files not tabixed or tbi
    nons = [x for x in nons if not x in fais]  # all non-fai files not tabixed or tbi
    fais = map(op.basename, fais)

    # ignore gzi
    nons = [n for n in nons if not n.endswith(".gzi")]  # just ignore gzi files

    gf = "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/{species}/{build}/{build}.genome".format(
        build=build, species=species
    )

    # TODO is this just repeating the _check_build call performed in the previous function?
    _check_build(species, build)

    for tbx in tbxs:
        print(":ggd:check-recipe: > checking %s" % tbx)
        try:
            sp.check_call(["check-sort-order", "--genome", gf, tbx], stderr=sys.stderr)
        except sp.CalledProcessError as e:
            sys.stderr.write(
                ":ggd:check-recipe: !!ERROR!!: in: %s(%s) with genome sort order compared to that specified in genome file\n"
                % (P, tbx)
            )
            remove_package_after_install(bz2, recipe_name, e.returncode)

    missing = []
    not_tabixed = []
    not_faidxed = []
    add_extra = False
    add_extra_files = []
    for n in nons:
        print(":ggd:check-recipe: > checking %s" % n)
        if n.endswith(
            (
                ".bed",
                ".bed.gz",
                ".vcf",
                ".vcf.gz",
                ".gff",
                ".gff.gz",
                ".gtf",
                ".gtf.gz",
                ".gff3",
                ".gff3.gz",
            )
        ):

            not_tabixed.append(
                ":ggd:check-recipe: !!ERROR!!: with: %s(%s) must be sorted, bgzipped AND tabixed.\n"
                % (P, n)
            )
        elif n.endswith((".fasta", ".fa", ".fasta.gz", ".fa.gz", ".fastq", ".fq", ".fastq.gz", ".fq.gz")):
            if (
                not op.basename(n + ".fai") in fais
                and not (re.sub("(.+).f(?:sta)?$", "\\1", op.basename(n)) + ".fai")
                in fais
            ):
                not_faidxed.append(
                    ":ggd:check-recipe: !!ERROR!!: with: %s(%s) fasta files must have an associated fai.\n"
                    % (P, n)
                )

        elif op.basename(n) not in extra_files and not any(
            fnmatch(op.basename(n), e) for e in extra_files
        ):
                print(
                    "\n:ggd:check-recipe: !!WARNING!!: %s(%s) unknown file and not in the extra/extra-files section of the yaml\n"
                    % (P, n) 
                )
                add_extra_files.append(op.basename(n))           
                add_extra = True

    if missing or not_tabixed or not_faidxed:
        print("\n".join(missing + not_tabixed + not_faidxed), file=sys.stderr)
        remove_package_after_install(bz2, recipe_name, 2)

    if add_extra:
        return add_extra_files
    else:
        return []


def check_yaml(recipe):
    """Method to check if the correct information is contained within the ggd recipe's meta.yaml file """

    ## Check yaml keys
    assert (
        "package" in recipe and "version" in recipe["package"]
    ), ":ggd:check-recipe: must specify 'package:' section with ggd version and package name"
    assert (
        "extra" in recipe
    ), ":ggd:check-recipe: must specify 'extra:' section with author and extra-files"
    assert (
        "about" in recipe and "summary" in recipe["about"]
    ), ":ggd:check-recipe: must specify an 'about/summary' section"
    assert (
        "identifiers" in recipe["about"]
    ), ":ggd:check-recipe: must specify an 'identifier' section in about"
    assert (
        "genome-build" in recipe["about"]["identifiers"]
    ), ":ggd:check-recipe: must specify 'about:' section with genome-build"
    assert (
        "species" in recipe["about"]["identifiers"]
    ), ":ggd:check-recipe: must specify 'about:' section with species"
    assert (
        "tags" in recipe["about"]
    ), ":ggd:check-recipe: must specify 'about:' section with tags"
    assert "keywords" in recipe["about"] and isinstance(
        recipe["about"]["keywords"], list
    ), ":ggd:check-recipe: must specify 'about:' section with keywords"

    ##Check tags
    assert (
        "genomic-coordinate-base" in recipe["about"]["tags"]
    ), ":ggd:check-recipe: must specify a genomic coordinate base for the files created by this recipe"
    assert (
        "data-version" in recipe["about"]["tags"]
    ), ":ggd:check-recipe: must specify the data version for the data files created by this recipe"
    assert (
        "data-provider" in recipe["about"]["tags"]
    ), ":ggd:check-recipe: must specify the data provider for the files created by this recipe"
    assert (
        "ggd-channel" in recipe["about"]["tags"]
    ), ":ggd:check-recipe: must specify the specific ggd channel for the recipe in the 'about:tags' section"
    assert (
        "file-type" in recipe["about"]["tags"]
    ),  ":ggd:check-recipe: The final data file types must be specified in the 'about:tags' section"
    assert (
        "final-files" in recipe["about"]["tags"]
    ),  ":ggd:check-recipe: All final data file must be specified in the 'about:tags' section"
    assert (
        "final-file-sizes" in recipe["about"]["tags"]
    ),  ":ggd:check-recipe: The size of each final data file must be specified in the 'about:tags' section"

    species, build, version, name = (
        recipe["about"]["identifiers"]["species"],
        recipe["about"]["identifiers"]["genome-build"],
        recipe["package"]["version"],
        recipe["package"]["name"],
    )
    version = version.replace(" ", "")
    version = version.replace(" ", "'")

    _check_build(species, build)
    return species, build, version, name
