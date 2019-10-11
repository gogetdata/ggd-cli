#-------------------------------------------------------------------------------------------------------------
## Import Statements
#-------------------------------------------------------------------------------------------------------------
from __future__ import print_function 
import sys
import os
import subprocess as sp
import glob
import traceback
import shutil
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
from .utils import prefix_in_conda
from .utils import get_conda_package_list
from .utils import update_installed_pkg_metadata

SPECIES_LIST = get_species()
#-------------------------------------------------------------------------------------------------------------
## Argument Parser
#-------------------------------------------------------------------------------------------------------------
def add_install(p):
    c = p.add_parser('install', help="Install a ggd data package", description="Install a ggd data package into the current or specified conda environment")
    c.add_argument("-c", "--channel", default="genomics", choices=get_ggd_channels(), 
                     help="The ggd channel the desired recipe is stored in. (Default = genomics)")
    c.add_argument("-v", "--version", default="-1", help="A specific ggd package version to install. If the -v flag is not used the latest version will be installed.")
    c.add_argument("-d", "--debug", action="store_true", help="(Optional) When the -d flag is set debug output will be printed to stdout.") 
    c.add_argument("--prefix", default=None, help="(Optional) The name or the full directory path to an existing conda environment where you want to install a ggd data pacakge. (Only needed if you want to install the data package into a different conda environment then the one you are currently in)")
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


def check_if_installed(ggd_recipe,ggd_jdict,ggd_version,prefix=None):
    """Method to check if the recipe has already been installed and is in the conda ggd storage path. 
        
    check_if_installed
    ==================
    This method is used to check if the ggd package has been installed and is located in the ggd storage path.
     If it is already installed the installation stops. If it is not detected then installation continues.
    """

    species = ggd_jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_recipe]["version"]

    CONDA_ROOT = prefix if prefix != None else conda_root()

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
    

def check_conda_installation(ggd_recipe,ggd_version,prefix=None):
    """Method used to check if the recipe has been installed using conda.

    check_conda_installation
    ========================
    This method is used to check if the ggd data package has been installed by the conda system,
     without being installed by the ggd system. If it has, the recipe needs to be uninstalled and 
     reinstalled. If not, the system continues to install the package using ggd.
    """

    ## Get the target prefix
    target_prefix = prefix if prefix != None else conda_root() 
    conda_package_list = get_conda_package_list(target_prefix) ## Get a list of installed ggd packages using conda list

    if ggd_recipe not in conda_package_list.keys(): 
        print("\n\t-> %s has not been installed by conda" %ggd_recipe)
        return(False)
    else:
        if ggd_version != "-1": ## Check if ggd version was designated 
            installed_version = conda_package_list[ggd_recipe]["version"]
            installed_build = conda_package_list[ggd_recipe]["build"]
            if installed_version != ggd_version:
                print("\n\t-> %s version %s has not been installed by conda" %(ggd_recipe,str(ggd_version)))
                return(False)
            else:
                print("\n\t-> %s version %s has been installed by conda on your system and must be uninstalled to proceed." %(ggd_recipe,str(ggd_version)))
                print("\t-> To reinstall run:\n\t\t $ ggd uninstall %s \n\t\t $ ggd install %s" %(ggd_recipe,ggd_recipe))
                if prefix != conda_root():
                    print("\t-> NOTE: You must activate the conda prefix {p} before running the uninstall command".format(p = target_prefix)) 
                sys.exit()
        else: 
            print("\n\t-> %s has been installed by conda on your system and must be uninstalled to proceed." %ggd_recipe)
            print("\t-> To reinstall run:\n\t\t $ ggd uninstall %s \n\t\t $ ggd install %s" %(ggd_recipe,ggd_recipe))
            if prefix != conda_root():
                print("\t-> NOTE: You must activate the conda prefix {p} before running the uninstall command".format(p = target_prefix)) 
            sys.exit()


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


def install_from_cached(ggd_recipe, ggd_channel,ggd_jdict,ggd_version,debug=False,prefix=None):
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
        bypass_satsolver_on_install(ggd_recipe,conda_channel,debug,prefix)

        get_file_locations(ggd_recipe,ggd_jdict,ggd_version,prefix)
        if prefix == None or os.path.normpath(prefix) == os.path.normpath(conda_root()):
            activate_enviroment_variables()


    except Exception as e:
        print("\n\t-> %s did not install properly. Review the error message:\n" %ggd_recipe)
        print(traceback.format_exc())
        target_prefix = conda_root() if prefix == None else prefix
        check_for_installation(ggd_recipe,ggd_jdict, target_prefix) ## .uninstall method to remove extra ggd files
        print("\n\t-> %s was not installed. Please correct the errors and try again." %ggd_recipe)
        sys.exit(1) 


    ## copy tarball and pkg file to target prefix
    if prefix != None and prefix != conda_root():
        print("\n\t-> Updating package metadata in user defined prefix")
        copy_pkg_files_to_prefix(prefix,ggd_recipe)

    ## Update installed metadata
    print("\n\t-> Updating installed package list")
    target_prefix = prefix if prefix != None else conda_root() 
    update_installed_pkg_metadata(prefix=target_prefix,remove_old=False,add_package=ggd_recipe)

    print("\n\t-> DONE")

    return(True)


def conda_install(ggd_recipe, ggd_channel,ggd_jdict,ggd_version, debug=False, prefix=None):
    """Method to install the recipe from the ggd-channel using conda
    
    conda_install
    ============
    This method is used to install the ggd recipe from the ggd conda channel using conda, if the files 
     have not been cached. 

    If installed correctly the method returns True
    """
    
    ## Get the target prefix
    target_prefix = prefix if prefix != None else conda_root() 

    ## Get conda version
    conda_version = get_required_conda_version()

    ## create install string
    conda_install_str = "conda=" + conda_version

    ## Add debug option
    conda_install_str += " --debug" if debug else "" 

    try:
        if ggd_version != "-1":
            print("\n\t-> Installing %s version %s" %(ggd_recipe,ggd_version))
            sp.check_call(["conda", "install", "-c", "ggd-"+ggd_channel, "-y", "--prefix", target_prefix,  ggd_recipe+"="+str(ggd_version)+"*", conda_install_str], stderr=sys.stderr, stdout=sys.stdout)
        else:
            print("\n\t-> Installing %s" %ggd_recipe)
            sp.check_call(["conda", "install", "-c", "ggd-"+ggd_channel, "-y", "--prefix", target_prefix, ggd_recipe, conda_install_str], stderr=sys.stderr, stdout=sys.stdout)

    except sp.CalledProcessError as e:
        sys.stderr.write("\n\t-> ERROR in install %s\n" %ggd_recipe)
        sys.stderr.write(str(e))
        sys.stderr.write("\n\t-> Removing files created by ggd during installation")
        check_for_installation(ggd_recipe,ggd_jdict,target_prefix) ## .uninstall method to remove extra ggd files
        sys.exit(e.returncode)

    ## copy tarball and pkg file to target prefix
    if prefix != None and prefix != conda_root():
        copy_pkg_files_to_prefix(prefix,ggd_recipe)

    ## Update installed metadata
    print("\n\t-> Updating installed package list")
    update_installed_pkg_metadata(prefix=target_prefix,remove_old=False,add_package=ggd_recipe)

    return(True)


def get_file_locations(ggd_recipe,ggd_jdict,ggd_version,prefix=None):
    """Method used to print the location of the installed files

    get_file_locations
    ==================
    This method is used to print the location of the data files installed for a reference 
    for the user.
    """

    species = ggd_jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_recipe]["version"]
    CONDA_ROOT = prefix if prefix != None else conda_root()
    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)

    try:
        assert os.path.exists(path)
    except AssertionError as e:
        print("\n\t->There was an error durring installation")

    print("\n\t-> Installation complete. The downloaded data files are located at:")
    print("\t\t%s" %path)
    if prefix != None:
        print("\n\t-> NOTE: These environment variables are specific to the %s conda environment and can only be accessed from within that environmnet" %prefix)
    print("\n\t-> A new environment variable that points to data package directory path has been created:")
    print("\t\t $ggd_%s_dir\n" %ggd_recipe.replace("-","_"))
    if os.path.exists(path):
        files = os.listdir(path)
        if len(files) == 1: ## A single file will have a env var 
            print("\n\t-> A new environment variable that points to the installed file has been created:")
            print("\t\t $ggd_%s_file\n" %ggd_recipe.replace("-","_"))
        elif len(files) == 2: ## A file with an associated index will have a env var
            if [True for x in files if ".csi" in x or ".tbi" in x or ".bai" in x or ".crai" in x or ".fai" in x or ".gzi" in x]:
                print("\n\t-> A new environment variable that points to the installed file has been created:")
                print("\t\t $ggd_%s_file\n" %ggd_recipe.replace("-","_").replace(".","_"))
            

def copy_pkg_files_to_prefix(prefix,pkg_name):
    """Method to copy the tar and package files from the current conda envrionment to the target prefix
    
    copy_pkg_files_to_prefix
    ========================
    This method is used to copy the tarball file and the pkg file from the current conda envrionment to the 
     target prefix if the prefix flag is set. This will support pkg info lookup for data managment when installing
     a package using the prefix flag

    Parameters:
    -----------
    1) prefix: The user set prefix 
    2) pkg_name: The name of the package being installed

    Returs:
    +++++++
    True: If files have been copied 
    False: If files were not copied (due to the prefix being the same as the current conda environment)
    Exception: If copying failed
    """

    CONDA_ROOT = conda_root()
        
    ## Check that the prefix is not the same as the conda root
    if CONDA_ROOT == prefix:
        return(False)

    ## Create the path if it does not already exists
    if os.path.exists(os.path.join(prefix,"pkgs")) == False:
        os.mkdir(os.path.join(prefix,"pkgs"))

    ## Get the file paths for the tar file and package
    data_packages = get_conda_package_list(prefix)
    version = str(data_packages[pkg_name]["version"])
    build = str(data_packages[pkg_name]["build"])

    tarfile_path = os.path.join(CONDA_ROOT,"pkgs","{}-{}-{}.tar.bz2".format(pkg_name,version,build))
    pkg_path = os.path.join(CONDA_ROOT,"pkgs","{}-{}-{}".format(pkg_name,version,build))

    ## Copy files to new location 
    shutil.copy2(tarfile_path, os.path.join(prefix,"pkgs"))
    shutil.copytree(pkg_path, os.path.join(prefix,"pkgs","{}-{}-{}".format(pkg_name,version,build)))

    return(True)
    

def install(parser, args):
    """Main method for installing a ggd data package

    install
    =======
    This method is the main method for running ggd install. It controls the different levels of install
    and file handeling. 
    """

    from .utils import conda_root, get_conda_prefix_path 

    ## Check the prefix is a real one
    if args.prefix != None:
        prefix_in_conda(args.prefix)
    else:
        args.prefix = conda_root()

    conda_prefix = get_conda_prefix_path(args.prefix) 

    print("\n\t-> Looking for %s in the 'ggd-%s' channel" %(args.name,args.channel))
    ## Check if the recipe is in ggd
    ggd_jsonDict = check_ggd_recipe(args.name,args.channel)
    if ggd_jsonDict == None:
        sys.exit()

    ## Check if the recipe is already installed  
    if not check_if_installed(args.name,ggd_jsonDict,args.version,conda_prefix):

        ## Check if conda has it installed on the system 
        if not check_conda_installation(args.name,args.version,conda_prefix):

            ## Set source environment prefix as an environment variable
            os.environ["CONDA_SOURCE_PREFIX"] = conda_root()  
            
            ## Check S3 bucket if version has not been set
            if args.version == "-1":
                if check_S3_bucket(args.name, ggd_jsonDict):
                    install_from_cached(args.name, args.channel, ggd_jsonDict, args.version, debug=args.debug,prefix=conda_prefix)           
                else:
                    conda_install(args.name, args.channel, ggd_jsonDict,args.version,debug=args.debug,prefix=conda_prefix)

                    get_file_locations(args.name,ggd_jsonDict,args.version,conda_prefix)
                    if conda_prefix == None or os.path.normpath(conda_prefix) == os.path.normpath(conda_root()):
                        activate_enviroment_variables()
                    print("\n\t-> DONE")
            else:
                conda_install(args.name, args.channel, ggd_jsonDict,args.version, debug=args.debug,prefix=conda_prefix)

                get_file_locations(args.name,ggd_jsonDict,args.version,conda_prefix)
                if conda_prefix == None or os.path.normpath(conda_prefix) == os.path.normpath(conda_root()):
                    activate_enviroment_variables()
                print("\n\t-> DONE")
            
    return(True) 
