#-------------------------------------------------------------------------------------------------------------
## Import Statements
#-------------------------------------------------------------------------------------------------------------
from __future__ import print_function 
import sys
import os
import subprocess as sp
import glob
import traceback
from .utils import conda_root
from .utils import get_species
from .utils import get_ggd_channels
from .utils import get_channel_data
from .utils import get_channeldata_url
from .utils import bypass_satsolver_on_install
from .utils import active_conda_env
from .show_env import activate_enviroment_variables 
from .search import load_json, load_json_from_url, search_packages
from .uninstall import remove_from_condaroot, check_for_installation
from .utils import get_required_conda_version

SPECIES_LIST = get_species()
#-------------------------------------------------------------------------------------------------------------
## Argument Parser
#-------------------------------------------------------------------------------------------------------------
def add_install(p):
    c = p.add_parser('install', help="install a data recipe from ggd")
    c.add_argument("-c", "--channel", default="genomics", choices=get_ggd_channels(), 
                     help="The ggd channel the desired recipe is stored in. (Default = genomics)")
    c.add_argument("-v", "--version", default="-1", help="A specific ggd package version to install. If the -v flag is not used the latest version will be installed.")
    c.add_argument("-d", "--debug", action="store_true", help="(Optional) When the -d flag is set debug output will be printed to stdout.") 
    c.add_argument("name", help="the name of the recipe to install")
    c.set_defaults(func=install)

#-------------------------------------------------------------------------------------------------------------
## Functions/Methods
#-------------------------------------------------------------------------------------------------------------


def check_ggd_recipe(ggd_recipe,ggd_channel):
    """Method used to check if the desired package is in the ggd repo using the repo metadata file

    check_ggd_recipe
    ================
    Method to check if the ggd recipe exists. Uses search_packages from search.py to 
     search the ggd-channel json file. If the recipe exists within the json file,
     the installation proceeds. If not, the instalation stops
    """

    CHANNEL_DATA_URL = get_channeldata_url(ggd_channel)
    jdict = load_json_from_url(CHANNEL_DATA_URL)
    package_list = [x[0] for x in search_packages(jdict, ggd_recipe)]
    if ggd_recipe in package_list:
        print("\n\t-> %s exists in the ggd-%s channel" %(ggd_recipe,ggd_channel))
        return(jdict)
    else:
        print("\n\t-> '%s' was not found in ggd-%s" %(ggd_recipe, ggd_channel))
        print("\t-> You can search for recipes using the ggd search tool: \n\t\t'ggd search -t %s'\n" %ggd_recipe)
        return(None)


def check_if_installed(ggd_recipe,ggd_jdict,ggd_version):
    """Method to check if the recipe has already been installed and is in the conda ggd storage path. 
        
    check_if_installed
    ==================
    This method is used to check if the ggd package has been installed and is located in the ggd storage path.
     If it is already installed the installation stops. If it is not detected then installation continues.
    """

    species = ggd_jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_recipe]["version"]

    CONDA_ROOT = conda_root()
    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)
    recipe_exists = glob.glob(path)
    if recipe_exists:
        # if the ggd_version designated to be installed does not match the installed version, install the designated version
        if ggd_version != version and ggd_version != "-1":
            return(False)
        else:
            print("\n\t-> '%s' is already installed." %ggd_recipe)
            print("\t-> You can find %s here: %s" %(ggd_recipe,path))
            sys.exit()
    else:
        print("\n\t-> %s version %s is not installed on your system" %(ggd_recipe, version))
        return(False)
    

def check_conda_installation(ggd_recipe,ggd_version):
    """Method used to check if the recipe has been installed using conda.

    check_conda_installation
    ========================
    This method is used to check if the ggd data package has been installed by the conda system,
     without being installed by the ggd system. If it has, the recipe needs to be uninstalled and 
     reinstalled. If not, the system continues to install the package using ggd.
    """

    conda_package_list = sp.check_output(["conda", "list"]).decode('utf8')
    recipe_find = conda_package_list.find(ggd_recipe)
    if recipe_find == -1:
        print("\n\t-> %s has not been installed by conda" %ggd_recipe)
        return(False)
    else:
        if ggd_version != "-1": ## Check if ggd version was designated 
            installed_version = conda_package_list[recipe_find:recipe_find+100].split("\n")[0].replace(" ","")[len(ggd_recipe)]
            if installed_version != ggd_version:
                print("\n\t-> %s version %s has not been installed by conda" %(ggd_recipe,str(ggd_version)))
                return(False)
            else:
                print("\n\t-> %s version %s has been installed by conda on your system and must be uninstalled to proceed." %(ggd_recipe,str(ggd_version)))
                print("\t-> To reinstall run:\n\t\t $ ggd uninstall %s \n\t\t $ ggd install %s" %(ggd_recipe,ggd_recipe))
                sys.exit()
        else: ## If version is not specified check if exact package in conda list
            start_index = conda_package_list.find(ggd_recipe) 
            end_index = start_index + len(ggd_recipe)
            ## Check if it really is the package, or something similar to the package 
            if conda_package_list[int(start_index) - 1] == "\n" and conda_package_list[int(end_index) + 1] == " ":
                print("\n\t-> %s has been installed by conda on your system and must be uninstalled to proceed." %ggd_recipe)
                print("\t-> To reinstall run:\n\t\t $ ggd uninstall %s \n\t\t $ ggd install %s" %(ggd_recipe,ggd_recipe))
                sys.exit()
            else: ## IF not exactly in conda list
                print("\n\t-> %s has not been installed by conda" %ggd_recipe)
                return(False)


def check_S3_bucket(ggd_recipe, ggd_jdict):
    """Method to check if the recipe is stored on the ggd S3 bucket. If so it installs from S3

    check_S3_bucket
    ==============
    This method is used to check if the recipe has been cached on aws S3 bucket. It returns true if the 
     the recipe is cached, and false if it is not. If it is cached the cached version will be installed. 
    """

    if "tags" in ggd_jdict["packages"][ggd_recipe]:
        if "cached" in ggd_jdict["packages"][ggd_recipe]["tags"]:
            if "uploaded_to_aws" in ggd_jdict["packages"][ggd_recipe]["tags"]["cached"]:
                print("\n\t-> The %s package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" %ggd_recipe)
                return(True)
    return(False)


def install_from_cached(ggd_recipe, ggd_channel,ggd_jdict,ggd_version,debug=False):
    """Method to install the ggd data package using a cached recipe

    install_from_cached
    ===================
    This method is used to install a ggd data package from a cached location. That is, a cached ggd recipe has 
     been created and can be installed. Installing using a cached recipe increases the install speed. This is
     because (1) data processing and curation has already been done and the resulting files are cached. (This removes
     the time it takes to processes the data). (2) With a cached recipe we can bypass conda's solve environment step. 

    If installed correctly the method returns True
    """

    conda_channel = "ggd-" + ggd_channel
    try:
        if debug:
            bypass_satsolver_on_install(ggd_recipe,conda_channel,debug=True)
        else:
            bypass_satsolver_on_install(ggd_recipe,conda_channel)

        get_file_locations(ggd_recipe,ggd_jdict,ggd_version)
        activate_enviroment_variables()
        print("\n\t-> DONE")

    except Exception as e:
        print("\n\t-> %s did not install properly. Review the error message:\n" %ggd_recipe)
        print(traceback.format_exc())
        check_for_installation(ggd_recipe,ggd_jdict) ## .uninstall method to remove extra ggd files
        print("\n\t-> %s was not installed. Please correct the errors and try again." %ggd_recipe)
        sys.exit(1) 

    return(True)


def conda_install(ggd_recipe, ggd_channel,ggd_jdict,ggd_version,debug=False):
    """Method to install the recipe from the ggd-channel using conda
    
    conda_install
    ============
    This method is used to install the ggd recipe from the ggd conda channel using conda, if the files 
     have not been cached. 

    If installed correctly the method returns True
    """
    
    conda_version = get_required_conda_version()
    conda_install_str = "conda=" + conda_version
    if ggd_version != "-1":
        print("\n\t-> Installing %s version %s" %(ggd_recipe,ggd_version))
        try:
            if debug:
                sp.check_call(["conda", "install", "-c", "ggd-"+ggd_channel, "-y", ggd_recipe+"="+str(ggd_version)+"*", conda_install_str, "--debug"], stderr=sys.stderr, stdout=sys.stdout)
            else:
                sp.check_call(["conda", "install", "-c", "ggd-"+ggd_channel, "-y", ggd_recipe+"="+str(ggd_version)+"*", conda_install_str], stderr=sys.stderr, stdout=sys.stdout)
        except sp.CalledProcessError as e:
            sys.stderr.write("\n\t-> ERROR in install %s\n" %ggd_recipe)
            sys.stderr.write(str(e))
            sys.stderr.write("\n\t-> Removing files created by ggd during installation")
            check_for_installation(ggd_recipe,ggd_jdict) ## .uninstall method to remove extra ggd files
            sys.exit(e.returncode)
    else:
        print("\n\t-> Installing %s" %ggd_recipe)
        try:
            if debug:
                sp.check_call(["conda", "install", "-c", "ggd-"+ggd_channel, "-y", ggd_recipe, conda_install_str, "--debug"], stderr=sys.stderr, stdout=sys.stdout)
            else:
                sp.check_call(["conda", "install", "-c", "ggd-"+ggd_channel, "-y", ggd_recipe, conda_install_str], stderr=sys.stderr, stdout=sys.stdout)
        except sp.CalledProcessError as e:
            sys.stderr.write("\n\t-> ERROR in install %s\n" %ggd_recipe)
            sys.stderr.write(str(e))
            sys.stderr.write("\n\t-> Removing files created by ggd during installation")
            check_for_installation(ggd_recipe,ggd_jdict) ## .uninstall method to remove extra ggd files
            sys.exit(e.returncode)

    return(True)


def get_file_locations(ggd_recipe,ggd_jdict,ggd_version):
    """Method used to print the location of the installed files

    get_file_locations
    ==================
    This method is used to print the location of the data files installed for a reference 
    for the user.
    """

    species = ggd_jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_recipe]["version"]
    CONDA_ROOT = conda_root()
    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)
    print("\n\t-> Installation complete. The downloaded data files are located at:")
    print("\t\t%s" %path)
    print("\n\t-> A new environment variable that points to data package directory path has been created:")
    print("\t\t $ggd_%s_dir\n" %ggd_recipe.replace("-","_"))
    if os.path.exists(path):
        files = os.listdir(path)
        if len(files) == 1: ## A single file will have a env var 
            print("\n\t-> A new environment variable that points to the installed file has been created:")
            print("\t\t $ggd_%s_file\n" %ggd_recipe.replace("-","_"))
        elif len(files) == 2: ## A file with an associated index will have a env var
            if [True for x in files if ".tbi" in x or ".bai" in x or ".crai" in x or ".fai" in x or ".gzi" in x]:
                print("\n\t-> A new environment variable that points to the installed file has been created:")
                print("\t\t $ggd_%s_file\n" %ggd_recipe.replace("-","_").replace(".","_"))
            

def install(parser, args):
    """Main method for installing a ggd data package

    install
    =======
    This method is the main method for running ggd install. It controls the different levels of install
    and file handeling. 
    """

    print("\n\t-> Looking for %s in the 'ggd-%s' channel" %(args.name,args.channel))
    ## Check if the recipe is in ggd
    ggd_jsonDict = check_ggd_recipe(args.name,args.channel)
    if ggd_jsonDict == None:
        sys.exit()
    ## Check if the recipe is already installed  
    if not check_if_installed(args.name,ggd_jsonDict,args.version):
        ## Check if conda has it installed on the system 
        if not check_conda_installation(args.name,args.version):
            ## Check S3 bucket if version has not been set
            if args.version == "-1":
                if check_S3_bucket(args.name, ggd_jsonDict):
                    install_from_cached(args.name, args.channel, ggd_jsonDict, args.version, debug=args.debug)           
                else:
                    if args.debug:
                        conda_install(args.name, args.channel, ggd_jsonDict,args.version,debug=True)
                    else:
                        conda_install(args.name, args.channel, ggd_jsonDict,args.version)

                    get_file_locations(args.name,ggd_jsonDict,args.version)
                    activate_enviroment_variables()
                    print("\n\t-> DONE")
            else:
                if args.debug:
                    conda_install(args.name, args.channel, ggd_jsonDict,args.version,debug=True)
                else:
                    conda_install(args.name, args.channel, ggd_jsonDict,args.version)

                get_file_locations(args.name,ggd_jsonDict,args.version)
                activate_enviroment_variables()
                print("\n\t-> DONE")
    return(True) 
