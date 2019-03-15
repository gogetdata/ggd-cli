from __future__ import print_function
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
from .utils import get_required_conda_version, check_output, conda_root
from .uninstall import check_for_installation

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

    c = p.add_parser('check-recipe', help="build, install, and check a recipe")
    c.add_argument("-d", "--debug", help="(Optional) Set the stdout log level to debug")
    c.add_argument("recipe_path", help="path to recipe directory (can also be path to the .bz2")
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
        files = next(os.walk(subdir))[2]
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
    if debug:
        out = check_output(['conda', 'build', "--debug", "--no-anaconda-upload", "-c", "ggd-genomics", path], stderr=sys.stderr)
    else:
        out = check_output(['conda', 'build', "--no-anaconda-upload", "-c", "ggd-genomics", path], stderr=sys.stderr)
    
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
    """

    conda_version = get_required_conda_version()
    conda_install = "conda=" + conda_version
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
                sp.check_call(['conda', 'install', '-v', '--use-local', '-y', recipe_name, conda_install, "--debug"], stderr=sys.stderr,
                            stdout=sys.stdout)
            else:
                sp.check_call(['conda', 'install', '-v', '--use-local', '-y', recipe_name, conda_install], stderr=sys.stderr,
                            stdout=sys.stdout)

    except Exception as e:
        print("\n\t-> %s did not install properly. \n\n\t->Error message:\n" %recipe_name)
        print(traceback.format_exc())
        print(e.message)

        ## Remove ggd files 
        recipe_dict = get_recipe_from_bz2(bz2)
        species = recipe_dict["about"]["identifiers"]["species"]
        genome_build = recipe_dict["about"]["identifiers"]["genome-build"]
        version = recipe_dict["package"]["version"]
        name = recipe_dict["package"]["name"]
        ggd_jdict = {"packages":{name:{"identifiers":{"species":species,"genome-build":genome_build},"version":version}}}
        check_for_installation(recipe_name,ggd_jdict) ## .uninstall method to remove extra ggd files
        print("\n\t-> Review the STDOUT and STDERR, correct the errors, and re-run $ggd check-recipes\n")

        ## Exit
        sys.exit(1)   


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
        recipe = yaml.load(recipe.read().decode())
    return recipe


def _check_build(species, build):
    #print("\nWarning: _check_build is deprecated\n")
    gf = "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/{species}/{build}/{build}.genome".format(build=build, species=species)
    try:
        ret = urlopen(gf)
        if ret.getcode() >= 400:
            raise Exception("%s at url: %s" % (ret.getcode(), gf))
    except:
        sys.stderr.write("ERROR: genome-build: %s not found in github repo.\n" % build)
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
    else:
        recipe = yaml.load(open(op.join(args.recipe_path, "meta.yaml")))
        if args.debug:
            bz2 = _build(args.recipe_path, recipe,debug=True)
        else:
            bz2 = _build(args.recipe_path, recipe)

    species, build, version = check_yaml(recipe)

    _check_build(species, build)

    install_path = op.join(conda_root(), "share", "ggd", species, build)

    before = list_files(install_path)

    if args.debug:
        _install(bz2,str(recipe['package']['name']),debug=True)
    else:
        _install(bz2,str(recipe['package']['name']))

    check_files(install_path, species, build, recipe['package']['name'],
                recipe['extra'].get('extra-files', []), before)

    print("\n\t****************************\n\t* Successful recipe check! *\n\t****************************\n")


def get_modified_files(files, before_files):
    """Method to check if the files installed during the installation process of a ggd packages are been modified """

    before_files = dict(before_files)
    files = [p for p, mtime in files if mtime != before_files.get(p, 0)]
    return files


def check_files(install_path, species, build, recipe_name,
                extra_files, before_files):
    """Method to check the presence of correct genomic files """

    P = "{species}/{build}:{recipe_name}".format(**locals())

    files = list_files(install_path)
    files = get_modified_files(files, before_files)
    if len(files) == 0:
        sys.stderr.write("ERROR: no modified files in %s\n" % install_path)
        sys.exit(2)
    print("modified files:\n\t :: %s\n\n" % "\n\t :: ".join(files))

    tbis = [x for x in files if x.endswith(".tbi")] # all tbi files
    nons = [x for x in files if not x.endswith(".tbi")] # all non tbi files

    tbxs = [x[:-4] for x in tbis if x[:-4] in nons] # names of files tabixed 

    nons = [x for x in nons if not x in tbxs] # files not tabixed or tbi
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
            sp.check_call(['check-sort-order', '--genome', gf, tbx], stderr=sys.stderr)
        except sp.CalledProcessError as e:
            sys.stderr.write("ERROR: in: %s(%s) with genome sort order compared to that specified in genome file\n" % (P, tbx))
            sys.exit(e.returncode)

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
        sys.exit(2)


def check_yaml(recipe):
    """Method to check if the correct information is contained within the ggd recipe's meta.yaml file """

    assert 'package' in recipe and "version" in recipe['package'], ("must specify 'package:' section with data version")
    assert 'extra' in recipe, ("must specify 'extra:' section with genome-build and species")
    assert 'about' in recipe and 'summary' in recipe['about'], ("must specify an 'about/summary' section")
    assert 'genome-build' in recipe['about']['identifiers'], ("must specify 'about:' section with species")
    assert 'species' in recipe['about']['identifiers'], ("must specify 'about:' section with species")
    assert 'keywords' in recipe['about'] and \
        isinstance(recipe['about']['keywords'], list), ("must specify 'about:' section with keywords")

    species, build, version = recipe['about']['identifiers']['species'], recipe['about']['identifiers']['genome-build'], recipe['package']['version']
    version = version.replace(" ", "")
    version = version.replace(" ", "'")

    _check_build(species, build)
    return species, build, version
