#-------------------------------------------------------------------------------------------------------------
## Import Statements
#-------------------------------------------------------------------------------------------------------------
from __future__ import print_function 
import sys
import os
import subprocess as sp
import glob
import shutil
import re
import tarfile
import yaml
import argparse
from .utils import conda_root
from .utils import get_species
from .utils import get_ggd_channels
from .utils import get_channel_data
from .utils import get_channeldata_url
from .search import load_json, load_json_from_url, search_packages
from .list_files import list_files

SPECIES_LIST = get_species()


#-------------------------------------------------------------------------------------------------------------
## Argument Parser
#-------------------------------------------------------------------------------------------------------------
def add_pkg_info(p):
    c = p.add_parser("pkg-info", help="List pkg info for an installed ggd-recipe")
    c.add_argument("-c", "--channel", default="genomics", choices=get_ggd_channels(), help="The ggd channel of the recipe to list info about (Default = genomics)")
    c.add_argument("-av", "--all_versions", action="store_true", help="(Optional) When the flag is set, list all ggd versions of a ggd-recipe for a specifc ggd-channel. (NOTE: -av flag does not accept arguments)")
    c.add_argument("-sr", "--show_recipe", action="store_true", help="(Optional) When the flag is set, the recipe will be printed to the stdout. This will provide info on where the data is hosted and how it was processed. (NOTE: -sr flag does not accept arguments)")
    c.add_argument("name", help="the name of the recipe to get info about")
    c.set_defaults(func=info)


#-------------------------------------------------------------------------------------------------------------
## Functions/Methods
#-------------------------------------------------------------------------------------------------------------

def list_all_versions(ggd_recipe, ggd_channel):
    """

    list_all_version
    ================
    Method used to list all available version of the ggd-recipe. All version will be printed.
    
    This method does not require that the package be installed.

    Parameters:
    ----------
    1) ggd_recipe: The ggd recipe name
    2) ggd_channel: The ggd channel to look at
    """
    try:
        pkg_versions = sp.check_output(['conda', 'search', ggd_recipe, '-c', "ggd-"+ggd_channel, '--override-channels']).decode('utf8')
        print("\n-> Listing all ggd-recipe version for the %s recipe in the ggd-%s channel" %(ggd_recipe,ggd_channel))
        print("\n\t ","\n\t- ".join(pkg_versions.split('\n')))
        return(True)
    except:
        print("No version information for %s in the ggd-%s channel" %(ggd_recipe, ggd_channel))
        return(False)


def check_if_ggd_recipe(ggd_recipe, ggd_channel):
    """Method to check if a ggd recipe is in designated ggd channel or not 

    check_if_ggd_recipe
    ===================
    Method used to identify if the desired ggd recipe is an actual recipe in the ggd channel or not

    Parameters:
    ----------
    1) ggd_recipe: The ggd recipe name
    2) ggd_channel: The ggd channel to look at
    """

    CHANNEL_DATA_URL = get_channeldata_url(ggd_channel)
    jdict = load_json_from_url(CHANNEL_DATA_URL)
    package_list = [x[0] for x in search_packages(jdict, ggd_recipe)]
    if ggd_recipe in package_list:
        return(True)
    else:
        print("\n\t-> The %s package is not in the ggd-%s channel. You can use 'ggd list-files', 'ggd install', or 'conda list' to identify" %(ggd_recipe,ggd_channel), 
            "if the package has been installed. If it has not been installed please install it")
        return(False)


def get_meta_yaml_info(tarball_info_object, ggd_recipe, ggd_channel):
    """Method to get information from the meta.yaml file of an installed ggd package

    get_meta_yaml_info
    =================
    method used to get info from a ggd-recipes meta.yaml file.
     this method assumes that recipe has been installed on the local machine
     the method will use a tarball info object and parse it 
      the info will be printed out to stdout
     
    Parameters:
    -----------
    1) tarball_info_object: a object made from using the tarfile module to extract files
    2) ggd_recipe: the ggd recipe name
    3) ggd_channel: the ggd channel name

    """

    yaml_dict = yaml.safe_load(tarball_info_object)
    species = yaml_dict["about"]["identifiers"]["species"]
    genome_build = yaml_dict["about"]["identifiers"]["genome-build"]
    keywords = yaml_dict["about"]["keywords"]
    data_version = ""
    cached = ""
    if "tags" in yaml_dict["about"]:
        if "data-version" in yaml_dict["about"]["tags"]: 
            data_version = yaml_dict["about"]["tags"]["data-version"]
        if "cached" in yaml_dict["about"]["tags"]:
            cached = yaml_dict["about"]["tags"]["cached"]
    summary = yaml_dict["about"]["summary"]
    version = yaml_dict["package"]["version"]
    build = yaml_dict["build"]["number"]
    build_requirements = yaml_dict["requirements"]["run"]
    run_requirements = yaml_dict["requirements"]["build"]

    path = os.path.join(conda_root(), "share", "ggd", species, genome_build, ggd_recipe, version)
    files_path = os.path.join(conda_root(), "share", "ggd", species, genome_build, ggd_recipe, version, "*")
    files = glob.glob(files_path)
    
    out = ""
    if data_version and cached:
        out = "\nGGD-Recipe: {}\nGGD-Channel: ggd-{}\nSummary: {}\nPkg Version: {}\nPkg Build: {}\nSpecies: {}\nGenome Build: {}\n\
Keywords: {}\nData Version: {}\nCached: {}\nPkg File Path: {}\nPkg Files: {}\n".format(ggd_recipe,ggd_channel,summary,version,
build,species,genome_build,", ".join(keywords),data_version,", ".join(cached),path,", ".join(files))
    elif data_version:
        out = "\nGGD-Recipe: {}\nGGD-Channel: ggd-{}\nSummary: {}\nPkg Version: {}\nPkg Build: {}\nSpecies: {}\nGenome Build: {}\n\
Keywords: {}\nData Version: {}\nPkg File Path: {}\nPkg Files: {}\n".format(ggd_recipe,ggd_channel,summary,version,
build,species,genome_build,", ".join(keywords),data_version,path,", ".join(files))
    else:
        out = "\nGGD-Recipe: {}\nGGD-Channel: ggd-{}\nSummary: {}\nPkg Version: {}\nPkg Build: {}\nSpecies: {}\nGenome Build: {}\n\
Keywords: {}\nPkg File Path: {}\nPkg Files: {}\n".format(ggd_recipe,ggd_channel,summary,version,
build,species,genome_build,", ".join(keywords),path,", ".join(files))

    print(out)
    return(True)
    

def print_recipe(tarball_info_object, ggd_recipe):
    """Method to print the ggd package original recipe script

    print_recipe
    ===========
    A method used to print the recipe from a tarball_info_object created from extracting 
     a file using the tarfile module. This method will print to stdout the recipe
     
    Parameters:
    ----------
    1) tarball_info_object: An tarball info object created from extracting a file using the tarfile module
    2) ggd_recipe: The ggd recipe name
    """

    print("\n%s recipe file:" %ggd_recipe)
    print("*****************************************************************************")
    for line in tarball_info_object:
        if isinstance(line, bytes): 
            print("* {}".format(line.decode('utf8').strip()))
        else:
            print("* {}".format(line.strip()))
    print("*****************************************************************************")
    print("NOTE: The recipe provided above outlines where the data was accessed and how it was processed\n\n")
    return(True)
 

def get_pkg_info(ggd_recipe, ggd_channel,show_recipe):
    """Method to get the package info from an installed package

    get_pkg_info
    ===========
    Method used to get ggd pkg info. It will open the pkg's tarfile and extract the meta.yaml file and the recipe
     script. Info from these files will be formated and sent to stdout
     
    Parameters:
    ----------
    1) ggd_recipe: The ggd recipe name
    2) ggd_channel: The ggd channel name
    3) show_recipe: A bool value, where if true will print the recipe.sh script
    """

    installed_pkg = sp.check_output(['conda', 'list', ggd_recipe]).decode('utf8')
    found = [x for x in re.sub(r"\s+","\t", installed_pkg.strip()).split("\t") if re.search(ggd_recipe+"$", x)] 
    if len(found) > 0:
        pkg_str = [x for x in installed_pkg.split("\n") if ggd_recipe in x][0]
        pkg_version = re.sub(" +","\t",pkg_str).split("\t")[1] # Pkg Version 
        pkg_build = re.sub(" +","\t",pkg_str).split("\t")[2] # Pkg Build
        pkg_tar_file = "{}-{}-{}.tar.bz2".format(ggd_recipe, pkg_version, pkg_build)
        CONDA_ROOT = conda_root()    
        file_path = os.path.join(CONDA_ROOT, "pkgs", pkg_tar_file)
        with tarfile.open(file_path, "r:bz2") as tarball_file:
            get_meta_yaml_info(tarball_file.extractfile(tarball_file.getmember("info/recipe/meta.yaml.template")), ggd_recipe, ggd_channel)
            if show_recipe:
                print_recipe(tarball_file.extractfile(tarball_file.getmember("info/recipe/recipe.sh")), ggd_recipe)
        return(True)
    else:
        print("\n-> %s is not downloaded on your system, or was downloaded incorrectly." %ggd_recipe)
        return(False)


def info(parser, args):
    """Main method to run list_pkg_info"""

    if check_if_ggd_recipe(args.name, args.channel):
        get_pkg_info(args.name, args.channel, args.show_recipe)
        if args.all_versions:
            list_all_versions(args.name, args.channel)
        return(True)
    else:
        return(False)


    
