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
from .utils import conda_root
from .utils import get_species
from .utils import get_ggd_channels
from .utils import get_channel_data
from .utils import get_channeldata_url
from .utils import check_for_internet_connection
from .search import load_json, load_json_from_url, search_packages
from .show_env import remove_env_variable, activate_enviroment_variables
from .utils import get_conda_package_list
from .utils import update_installed_pkg_metadata

SPECIES_LIST = get_species()

#-------------------------------------------------------------------------------------------------------------
## Argument Parser 
#-------------------------------------------------------------------------------------------------------------
def add_uninstall(p):
    c = p.add_parser('uninstall', help="Uninstall a ggd data data package", description="Use ggd to uninstall a ggd data package installed in the current conda environment")
    c.add_argument("-c", "--channel", default="genomics", choices=get_ggd_channels(), help="The ggd channel of the recipe to uninstall. (Default = genomics)")
    c.add_argument("name", help="the name of the recipe to uninstall")
    c.set_defaults(func=uninstall)


#-------------------------------------------------------------------------------------------------------------
## Functions/Methods 
#-------------------------------------------------------------------------------------------------------------


def get_channeldata(ggd_recipe,ggd_channel):
    """Method to get the conda channel data for the specific ggd/conda channel for the designated ggd recipe

    get_channeldata
    ===============
    Method to get the channel data and check if the recipe is within that channel.
     This method is to identify the files installed during installation, but that 
     won't be removed by normal uninstalling. These files will be removed by the 
     check_for_installation() method if it is found within the channeldata.json file

    """

    jdict = {'channeldata_version': 1, 'packages': {}}
    if check_for_internet_connection(): 
        CHANNEL_DATA_URL = get_channeldata_url(ggd_channel)
        jdict = load_json_from_url(CHANNEL_DATA_URL)
    else:
        try:
            ## If no internet connection just load from the local file
            jdict = load_json(get_channel_data(ggd_channel)) 
        except:
            pass

    package_list = []
    if len(jdict["packages"].keys()) > 0:
        package_list = [x[0] for x in search_packages(jdict, ggd_recipe)]

    if ggd_recipe in package_list:
        return(jdict)
    else:
        print("\n\t-> %s is not in the ggd-%s channel" %(ggd_recipe,ggd_channel))
        similar_pkgs = get_similar_pkg_installed_by_conda(ggd_recipe)
        if len(similar_pkgs) > 0:
            print("\n\t-> Packages installed on your system that are similar include:\n\t\t Package\tChannel\n\t\t-%s" %"\n\t\t-".join([x for x in similar_pkgs.split("\n")]))
            print("\n\t-> If one of these packages is the desired package to uninstall please re-run ggd uninstall with the desired package name and correct ggd channel name")
            print("\n\t-> Note: If the the package is not a part of a ggd channel run 'conda uninstall <pkg>' to uninstall")
            print("\n\t\t-> GGD channels include: %s" %",".join(get_ggd_channels()))
        else:
            print("\n\t-> Unable to find any package similar to the package entered. Use 'ggd search' or 'conda find' to identify the right package")
            print("\n\t-> This package may not be installed on your system")
        return(False)
        

def get_similar_pkg_installed_by_conda(ggd_recipe):
    """Method to get a list of similarly installed package names, refereing to package installed by conda

    get_similar_pkg_installed_by_conda
    ==================================
    Method to identify if there are similar packages to the one provided installed by conda that could be 
     uninstalled. Porvides a list of potential pkg names
     
    Parameters:
    ----------
    1) ggd_recipe: The ggd_recipe name. (May not be an actuall ggd_recipe)
     
    Returns:
    +++++++
    A string of pkgs and channels, with each pkg-channel spereated from another by a new line
    """

    conda_package_list = sp.check_output(["conda", "list"]).decode('utf8').split("\n")
    ## Index 0 = name, index -1 = channel name
    return("\n".join([pkg.split(" ")[0]+"\t"+pkg.split(" ")[-1] for pkg in conda_package_list if ggd_recipe in pkg]))


def check_conda_installation(ggd_recipe):
    """Method to check if the ggd package was installed with conda

    check_conda_installation
    ========================
    Method used to check if the recipe has been installed with conda. If so, it uses conda to uninstall the recipe
    """

    #conda_package_set = set(sp.check_output(["conda", "list"]).decode('utf8').strip().replace("\n"," ").split(" "))
    #if ggd_recipe in conda_package_set:
    installed_ggd_packages = get_conda_package_list(conda_root()).keys() ## Get the installed ggd data package names
    if ggd_recipe in installed_ggd_packages:
        print("\n\t-> %s is installed by conda on your system" %ggd_recipe)
        return(conda_uninstall(ggd_recipe))

    else:
        print("\n\t-> %s is NOT installed on your system" %ggd_recipe)
        

def conda_uninstall(ggd_recipe):
    """Method use to uninstall the ggd recipe using conda

    conda_uninstall
    ===============
    Method used to uninstall ggd recipe using conda
    """

    print("\n\t-> Uninstalling %s" %ggd_recipe)
    try:
        return(sp.check_call(["conda", "uninstall", "-y", ggd_recipe], stderr=sys.stderr, stdout=sys.stdout))
    except sp.CalledProcessError as e:
        sys.stderr.write("ERROR in uninstall %s" %ggd_recipe)
        sys.stderr.write(str(e))
        sys.exit(e.returncode)


def check_for_installation(ggd_recipe,ggd_jdict):
    """Method to check for and processes ggd package if it is installed

    check_for_installation
    =================
    Method used to remove extra files created during recipe installation, but that are not 
     removed during normal uninstallation. 
    This method depends on the get_channeldata method. If the recipe is not found in the 
     channeldata.json file the extra files will not be removed. 
    """

    species = ggd_jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_recipe]["version"]

    CONDA_ROOT = conda_root()
    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)
    recipe_exists = glob.glob(path)
    if recipe_exists:
        print("\n\t-> Removing %s version %s file(s) from ggd recipe storage" %(ggd_recipe,str(version)))
        shutil.rmtree(path)
        remove_from_condaroot(ggd_recipe,version)
        dir_env_var = "ggd_" + ggd_recipe + "_dir"
        remove_env_variable(dir_env_var)
        file_env_var = "ggd_" + ggd_recipe + "_file"
        remove_env_variable(file_env_var)
    else:
        print("\n\t-> %s is not in the ggd recipe storage" %ggd_recipe)


def remove_from_condaroot(ggd_recipe,version):
    """Method to use conda to remove an installed ggd package from the conda root. This is a method for ggd package file handling

    remove_from_condaroot
    ====================
    Method used to remove the recipe's extra files created during installation, but that are not removed 
     when uninstalled. 
    """

    find_list = sp.check_output(['find', conda_root(), '-name', ggd_recipe+"-"+str(version)+"*"]).decode('utf8').strip().split("\n")
    ## Filter the list by conda env
    croot = conda_root()
    filtered_list = []
    for path in find_list:
        if croot in path:
            if croot+"/envs/" not in path: ## If the conda env root is in the path, and conda env root/env/ is not in the path, then add it to the filtered list
                filtered_list.append(path)
    print("\n\t-> Deleteing %d items of %s version %s from your conda root" %(len(filtered_list),ggd_recipe,version))
    ## Remove files
    for path in filtered_list:
        if str(croot)+"/env/" not in path:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)


def uninstall(parser, args):
    """Main method for uninstall command

    uninstall
    =========
    Main method used to check if the recipe is installed, uninstall the recipe, and remove extra recipe files
    """

    print("\n\t-> Checking for installation of %s" %args.name)
    ## Get the channeldata.json file in dictionary form
    ggd_jsonDict = get_channeldata(args.name,args.channel)
    if ggd_jsonDict == False:
        sys.exit()
    ## Check if insatlled through conda
    check_conda_installation(args.name)
    ## Check if the recipe is in file system   
    if len(ggd_jsonDict) > 0:
        check_for_installation(args.name,ggd_jsonDict)
    else:
        print("\n\t-> Skipping package removal from system step")

    ## Update installed package list
    print("\n\t-> Updating installed package list")
    update_installed_pkg_metadata(exclude_pkg = args.name)

    print("\n\t-> DONE")

    return(True)
                

