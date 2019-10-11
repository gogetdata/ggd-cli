from __future__ import print_function
import argparse
import sys
import os
import os.path as op
import tarfile
import re
import traceback
import subprocess as sp
import yaml 
import locale
from fnmatch import fnmatch
from .utils import get_required_conda_version, check_output, conda_root, check_for_internet_connection, get_species
from .uninstall import check_for_installation
from .install import check_ggd_recipe

#---------------------------------------------------------------------------------------------------
# urlib setup based on system version
#---------------------------------------------------------------------------------------------------
if sys.version_info[0] < 3:
    import urllib
    urlopen = urllib.urlopen
else:
    from urllib.request import urlopen

#---------------------------------------------------------------------------------------------------
# Argument parser 
#---------------------------------------------------------------------------------------------------

def add_check_recipe(p):
    """Argument method used to add check-recipes as a module arugment/function """

    c = p.add_parser('check-recipe', help="Build, install, check, and test a ggd data recipe", description="Convert a ggd recipe created from `ggd make-recipe` into a data package. Test both ggd data recipe and data package")
    c.add_argument("-d", "--debug", action="store_true", help="(Optional) Set the stdout log level to debug")
    c.add_argument("-du", "--dont_uninstall", action="store_true", help="(Optional) By default the newly installed local ggd data package is uninstalled after the check has finished. To bypass this uninstall step (to keep the local package installed) set this flag \"--dont_uninstall\"")
    c.add_argument("--add-md5sum-for-checksum", action="store_false", required=False, help=argparse.SUPPRESS)
    c.add_argument("recipe_path", help="path to recipe directory (can also be path to the .bz2)")

    c.set_defaults(func=check_recipe)

#---------------------------------------------------------------------------------------------------
# Functions/methods
#---------------------------------------------------------------------------------------------------

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
        #files = next(os.walk(subdir))[2]
        files_list = next(os.walk(subdir))
        files = files_list[2]
        if (len(files) > 0):
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

    vs = [x for x in check_output(['conda', 'info']).split("\n") if
            "platform :" in x]
    assert len(vs) == 1, vs
    return vs[0].split("platform :")[1].strip()


def _build(path, recipe,debug=False):
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

    sp.check_call(['conda','build','purge'], stderr=sys.stderr, stdout = sys.stdout)
    try:
        if debug:
            out = check_output(['conda', 'build', "--debug", "--no-anaconda-upload", "-c", "ggd-genomics", path], stderr=sys.stderr)
        else:
            out = check_output(['conda', 'build', "--no-anaconda-upload", "-c", "ggd-genomics", path], stderr=sys.stderr)

    except Exception as e:
        ## Check all requirenments for ggd dependencies
        print("Rolling back ggd dependencies")
        for d in recipe["requirements"]["build"]:  
            try:
                ggd_jdict = check_ggd_recipe(d,ggd_channel="genomics") 
            except SystemExit as e:
                ggd_jdict = None

            if ggd_jdict != None:
                print("Rolling back %s" %d)
                ## Remove ggd files 
                check_for_installation(d,ggd_jdict) ## .uninstall method to remove extra ggd files
        print("\n\t-> Review the STDOUT and STDERR, correct the errors, and re-run $ggd check-recipes\n")
        ## Exit
        sys.exit(5)   
    
    pattern = "Package:.+"
    result = re.search(pattern, out)
    if result == None: ## If pattern not found
        pattern = "Packaging.+"
        result = re.findall(pattern, out)
    
    name = result[-1].split()[1].replace(".tar.bz2","") + ".tar.bz2" #name of the file: exapmle = hg19-phastcons-1-0.tar.bz2

    platform = "noarch" if "noarch" in recipe['build'] else conda_platform() ## Check for noarch platform
    path = op.join(conda_root(), "conda-bld", platform)

    return os.path.join(path, name)


def _install(bz2,recipe_name,debug=False):
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

    conda_version = get_required_conda_version()
    conda_install = "conda=" + conda_version

    ## See if it is already installed 
    pkg_out = sp.check_output(["conda list {}".format(recipe_name)], shell=True).decode("utf8")
    if recipe_name in pkg_out: ## If already installed
        return(False)

    ## Set CONDA_SOURCE_PREFIX environment variable
    os.environ["CONDA_SOURCE_PREFIX"] = conda_root() 

    ## Install the new recipe
    try:
        if conda_version != -1:
            if debug:
                sp.check_call(['conda', 'install', '-v', '--use-local', '-y', recipe_name, conda_install, "--debug"], stderr=sys.stderr,
                            stdout=sys.stdout)
            else:
                sp.check_call(['conda', 'install', '-v', '--use-local', '-y', recipe_name, conda_install], stderr=sys.stderr,
                            stdout=sys.stdout)
        else:
            if debug:
                sp.check_call(['conda', 'install', '-v', '--use-local', '-y', recipe_name, "--debug"], stderr=sys.stderr,
                            stdout=sys.stdout)
            else:
                sp.check_call(['conda', 'install', '-v', '--use-local', '-y', recipe_name], stderr=sys.stderr,
                            stdout=sys.stdout)

    except Exception as e:
        print(e)
        print("\n\t-> %s did not install properly. \n\n\t->Error message:\n" %recipe_name)
        print(traceback.format_exc())

        ## Remove ggd files 
        recipe_dict = get_recipe_from_bz2(bz2)
        species = recipe_dict["about"]["identifiers"]["species"]
        genome_build = recipe_dict["about"]["identifiers"]["genome-build"]
        version = recipe_dict["package"]["version"]
        name = recipe_dict["package"]["name"]
        ggd_jdict = {"packages":{name:{"identifiers":{"species":species,"genome-build":genome_build},"version":version}}}
        try:
            check_for_installation(recipe_name,ggd_jdict) ## .uninstall method to remove extra ggd files
        except Exception as e:
            print(e)

        print("\n\t-> Review the STDOUT and STDERR, correct the errors, and re-run $ggd check-recipes\n")
        ## Exit
        sys.exit(1)   

    return(True)


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

    info = None
    with tarfile.open(fbz2, mode="r|bz2") as tf:
        for info in tf:
            # this was changed recently in conda/conda-build
            if info.name in ("info/recipe/meta.yaml", "info/meta.yaml"):
                break
        else:
            print("Error: Incorrect tar.bz format.", file=sys.stderr)
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

    if check_for_internet_connection():
        gf = "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/{species}/{build}/{build}.genome".format(build=build, species=species)
        try:
            ret = urlopen(gf)
            if ret.getcode() >= 400:
                raise Exception("%s at url: %s" % (ret.getcode(), gf))
        except:
            sys.stderr.write("ERROR: genome-build: %s not found in github repo for the %s species.\n" %(build,species))
            raise
        return(True)
    else: ## If no internet conection (mostly for make-recipe in an internet free context)
        ## Get a dictionary with keys as species and values as genome builds
        species_build_dict = get_species(full_dict=True) 
        if build in species_build_dict[species]:
            return(True)
        else:
            sys.stderr.write("ERROR: genome-build: %s not found in github repo for the %s species.\n" %(build,species))
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
        args.add_md5sum_for_checksum = False ## If bz2, checksum should have already been calculated. 
    else:
        recipe = yaml.safe_load(open(op.join(args.recipe_path, "meta.yaml")))
        if args.debug:
            bz2 = _build(args.recipe_path, recipe,debug=True)
        else:
            bz2 = _build(args.recipe_path, recipe)

    species, build, version, recipe_name = check_yaml(recipe)

    _check_build(species, build)

    install_path = op.join(conda_root(), "share", "ggd", species, build, recipe_name, version)

    before = list_files(install_path)

    if args.debug:
        new_installed = _install(bz2,str(recipe['package']['name']),debug=True)
    else:
        new_installed = _install(bz2,str(recipe['package']['name']))

    ## Check if previous package is already installed or it is a new installation
    if new_installed:
        check_files(install_path, species, build, recipe['package']['name'],
                    recipe['extra'].get('extra-files', []), before, bz2)

        ## Check final installed data files
        check_final_files(install_path,recipe)
    
        ## Add mdfsum
        if args.add_md5sum_for_checksum:
            add_to_checksum_md5sums(install_path, recipe, op.join(args.recipe_path,"checksums_file.txt"))      

            print("\n\t****************************\n\t* Successful recipe check! *\n\t****************************\n")

        ## If skipping md5sum addition, check md5sum for each file
        else:
            ## Check that the checksum in the .bz2 file has a filled checksum file 
            from .utils import get_checksum_dict_from_tar, data_file_checksum
            checksum_dict = get_checksum_dict_from_tar(bz2)
            if not data_file_checksum(install_path, checksum_dict):
                print("\nForcing uninstall")
                args.dont_uninstall = False
                print("\n\t!!!!!!!!!!!!!!!!!!!!!!!!\n\t! FAILED recipe check !\n\t!!!!!!!!!!!!!!!!!!!!!!!!\n")

            else:
                print("\n\t****************************\n\t* Successful recipe check! *\n\t****************************\n")


    else: ## if already installed 
        print("\nPackage already installed on your system")
        print("\nIf the \"-du\" flag (dont_uninstall) is NOT set this package will be uninstalled") 
        print("\nTo recheck this recipe")
        print(" 1) Uninstall the reicpe with: \n\t$ ggd check-recipe {} \tNOTE: Make sure the \"-du\" flag is NOT set".format(args.recipe_path))
        print(" 2) Run check recipes again once the local package is uninstalled (From step 1): \n\t $ggd check-recipe {} \tNOTE: With or without the \"-du\" flag.".format(args.recipe_path))


    if args.dont_uninstall == False:
        print("\n\n The --dont_uninstall flag was not set \n\n Uninstalling the locally built ggd data package")

        recipe_dict = get_recipe_from_bz2(bz2)
        species = recipe_dict["about"]["identifiers"]["species"]
        genome_build = recipe_dict["about"]["identifiers"]["genome-build"]
        version = recipe_dict["package"]["version"]
        name = recipe_dict["package"]["name"]
        ggd_jdict = {"packages":{name:{"identifiers":{"species":species,"genome-build":genome_build},"version":version}}}
        try:
            check_for_installation(name,ggd_jdict) ## .uninstall method to remove extra ggd files
        except Exception as e:
            print(e)
    else:
        recipe_dict = get_recipe_from_bz2(bz2)
        name = recipe_dict["package"]["name"]
        print("\n\n {} will remain installed on your system as a local data package.".format(name))

    return(True)


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
    import glob
    from .utils import get_file_md5sum 

    with open(recipe_checksum_file_path, "w") as cs_file:
        installed_files = glob.glob(op.join(installed_dir_path,"*"))

        ## Check the number of files are the same between the yaml file and the acutal data files
        final_files = yaml_file["about"]["tags"]["final-files"] 
        assert len(final_files) == len(installed_files), ("The number of installed files does not match the number of final files listed in the recipe." +
            " Number of installed files = {i}, Number of final files in recipe = {f}".format(i= len(installed_files), f= len(final_files)))

        for ifile in installed_files:
            cs_file.write(op.basename(ifile)+"\t"+get_file_md5sum(ifile)+"\n")

    return(True)


def check_final_files(installed_dir_path,yaml_file):
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
    import glob

    installed_files = glob.glob(op.join(installed_dir_path,"*"))

    final_files = yaml_file["about"]["tags"]["final-files"] 

    ## Check that there are the same number of files as files installed. 
    assert len(final_files) == len(installed_files), ("The number of installed files does not match the number of final files listed in the recipe." +
        " Number of installed files = {i}, Number of final files in recipe = {f}".format(i= len(installed_files), f= len(final_files)))

    ## Test the file exists 
    for ffile in final_files:
        ffile_path = op.join(installed_dir_path,ffile)
        assert ffile_path in installed_files, ("The {ff} file designated in the recipe is not one of the installed files".format(ff=ffile))
        assert os.path.exists(ffile_path), ("The {ff} file designated in the recipes does not exists as an installed file".format(ff=ffile))
        assert os.path.isfile(ffile_path), ("The {ff} file designated in the recipes is not a file in the installed path".format(ff=ffile))

    return(True)


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

    print("\nPost-installation checks have failed. Rolling back installation")

    recipe_dict = get_recipe_from_bz2(bz2)
    species = recipe_dict["about"]["identifiers"]["species"]
    genome_build = recipe_dict["about"]["identifiers"]["genome-build"]
    version = recipe_dict["package"]["version"]
    name = recipe_dict["package"]["name"]
    ggd_jdict = {"packages":{name:{"identifiers":{"species":species,"genome-build":genome_build},"version":version}}}
    try:
        check_for_installation(recipe_name,ggd_jdict) ## .uninstall method to remove extra ggd files
    except Exception as e:
        print(e)

    print("\n\t-> Review the STDOUT and STDERR, correct the errors, and re-run $ggd check-recipes\n")
    ## Exit
    sys.exit(exit_num)   


def check_files(install_path, species, build, recipe_name,
                extra_files, before_files, bz2):
    """Method to check the presence of correct genomic files """

    P = "{species}/{build}:{recipe_name}".format(**locals())

    files = list_files(install_path)
    files = get_modified_files(files, before_files)
    if len(files) == 0:
        sys.stderr.write("ERROR: no modified files in %s\n" % install_path)
        remove_package_after_install(bz2,recipe_name,2)

    print("modified files:\n\t :: %s\n\n" % "\n\t :: ".join(files))

    tbis = [x for x in files if x.endswith(".tbi")] # all tbi files

    nons = [x for x in files if not x.endswith(".tbi")] # all non tbi files

    tbxs = [x[:-4] for x in tbis if x[:-4] in nons] # names of files tabixed 

    base_tbx_tbi = [x[:-3] for x in tbxs if x[:-3] in nons] # Name of files that are bgzip and tabix3d 

    nons = [x for x in nons if x not in tbxs] # files not tabixed or tbi
    nons = [x for x in nons if x not in base_tbx_tbi] # files not tabixed or tbi

    # check for fais?
    fais = [x for x in nons if x.endswith(".fai")] #all fai files not tabixed or tbi
    nons = [x for x in nons if not x in fais] # all non-fai files not tabixed or tbi
    fais = map(op.basename, fais)

    # ignore gzi
    nons = [n for n in nons if not n.endswith('.gzi')] # just ignore gzi files

    gf = "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/{species}/{build}/{build}.genome".format(build=build, species=species)
    
    # TODO is this just repeating the _check_build call performed in the previous function?
    _check_build(species, build)

    for tbx in tbxs:
        print("> checking %s" % tbx)
        try:
            sp.check_call(["check-sort-order", "--genome", gf, tbx], stderr=sys.stderr)
        except sp.CalledProcessError as e:
            sys.stderr.write("ERROR: in: %s(%s) with genome sort order compared to that specified in genome file\n" % (P, tbx))
            remove_package_after_install(bz2,recipe_name,e.returncode)

    missing = []
    not_tabixed = []
    not_faidxed = []
    for n in nons:
        print("> checking %s" % n)
        if n.endswith((".bed", ".bed.gz", ".vcf", ".vcf.gz", ".gff",
                       ".gff.gz", ".gtf", ".gtf.gz", ".gff3", ".gff3.gz")):

            not_tabixed.append("ERROR: with: %s(%s) must be sorted, bgzipped AND tabixed.\n" % (P, n))
        elif n.endswith((".fasta", ".fa", ".fasta.gz", ".fa.gz")):
            if not op.basename(n + ".fai") in fais and not (re.sub("(.+).fa(?:sta)?$",
                                                       "\\1",
                                                       op.basename(n)) + ".fai") in fais:
                not_faidxed.append("ERROR: with: %s(%s) fasta files must have an associated fai.\n" % (P, n))

        elif op.basename(n) not in extra_files and not any(fnmatch(op.basename(n), e) for e in extra_files):
                missing.append("ERROR: %s(%s) unknown file and not in the extra/extra-files section of the yaml\n" % (P, n))

    if missing or not_tabixed or not_faidxed:
        print("\n".join(missing + not_tabixed + not_faidxed), file=sys.stderr)
        remove_package_after_install(bz2,recipe_name,2)

    return(True)


def check_yaml(recipe):
    """Method to check if the correct information is contained within the ggd recipe's meta.yaml file """

    ## Check yaml keys 
    assert 'package' in recipe and "version" in recipe['package'], ("must specify 'package:' section with ggd version and package name")
    assert 'extra' in recipe, ("must specify 'extra:' section with author and extra-files")
    assert 'about' in recipe and 'summary' in recipe['about'], ("must specify an 'about/summary' section")
    assert 'identifiers' in recipe['about'], ("must specify an 'identifier' section in about")
    assert 'genome-build' in recipe['about']['identifiers'], ("must specify 'about:' section with genome-build")
    assert 'species' in recipe['about']['identifiers'], ("must specify 'about:' section with species")
    assert 'tags' in recipe['about'], ("must specify 'about:' section with tags")
    assert 'keywords' in recipe['about'] and \
        isinstance(recipe['about']['keywords'], list), ("must specify 'about:' section with keywords")

    ##Check tags
    assert "genomic-coordinate-base" in recipe["about"]["tags"], ("must specify a genomic coordinate base for the files created by this recipe")
    assert "data-version" in recipe["about"]["tags"], ("must specify the data version for the data files created by this recipe")
    assert "data-provider" in recipe["about"]["tags"], ("must specify the data provider for the files created by this recipe")
    assert "file-type" in recipe["about"]["tags"], ("must specify the file types for the files created by this recipe")
    assert "final-files" in recipe["about"]["tags"], ("must specify the final files created by this recipe")
    assert 'ggd-channel' in recipe['about']['tags'], ("must specify the specific ggd channel for the recipe in the 'about:tags' section")

    species, build, version, name  = recipe['about']['identifiers']['species'], \
                                     recipe['about']['identifiers']['genome-build'], \
                                     recipe['package']['version'], \
                                     recipe['package']['name']
    version = version.replace(" ", "")
    version = version.replace(" ", "'")

    _check_build(species, build)
    return species, build, version, name
