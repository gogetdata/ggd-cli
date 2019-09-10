#-------------------------------------------------------------------------------------------------------------
## Import Statements
#-------------------------------------------------------------------------------------------------------------
from __future__ import print_function
import sys
import os
import argparse
import json
import re
from .utils import conda_root, prefix_in_conda, update_installed_pkg_metadata, get_conda_package_list 

GGD_INFO = "share/ggd_info"
METADATA = "channeldata.json"


#-------------------------------------------------------------------------------------------------------------
## Argument Parser 
#-------------------------------------------------------------------------------------------------------------
def add_list_installed_packages(p):
    c = p.add_parser('list', help="List the ggd data package(s) that are currently installed in a specific conda environment", description="Get a list of ggd data packages installed in the current or specified conda prefix/environment.")
    c.add_argument("-p", "--pattern",  help="(Optional) pattern to match the name of the ggd data package.")
    c.add_argument("--prefix", default=None, help="(Optional) The full directory path to an conda environment where a ggd recipe is stored. (Only needed if not getting file paths for files in the current conda enviroment)") 
    c.set_defaults(func=list_installed_packages)


#-------------------------------------------------------------------------------------------------------------
## Functions/Methods 
#-------------------------------------------------------------------------------------------------------------


def load_json(jfile):
    """Method to load a json file into a dictionary

    load_json
    =========
    Method to load a json file 

    Parameters:
    ---------
    1) jfile: The path to the json file

    Returns:
    1) A dictionary of a json object 
    """

    with open(jfile) as jsonFile:
       return(json.load(jsonFile))


def get_environment_variables(prefix):
    """Method to get ggd data package environment variables in a user specified conda environment/prefix

    get_environment_variables
    =========================
    Method to get the environment variables for each installed data package in a spefic conda environment

    Parameters:
    -----------
    1) prefix: The conda environment/prefix to get environment variables for 

    Returns:
    ++++++++
    1) A dicionary with each key == env_var, and values == the path the environment variable is for
    """

    env_var_path = os.path.join(prefix,"etc","conda","activate.d","env_vars.sh")
    env_vars = {}
    try:
        with open(env_var_path, "r") as env_file:
            for var in env_file:
                var_array = var.strip().split()
                if len(var_array) >= 2:
                    var_item_array = var_array[1].split("=")
                if len(var_item_array) >= 1:
                    env_vars[var_item_array[0]] = var_item_array[1]
    except(IOError, ValueError):
        return(None)

    ## Key = env_var, value = path
    return(env_vars)
    

def list_pkg_info(pkg_names, pkgs_dict, env_vars, conda_list, prefix, prefix_set=False):
    """Method to identify and display available data packages in a specific conda environmnet

    list_pkg_info
    =============
    Method to display the ggd data packages installed in a specific conda environemnt. If the 
     prefix is not set, the packages in the current environment will be dispalyed. If the --pattern
     flag is set, the package names will be filtered prior to this method.

    Parameters:
    -----------
    1) pkg_names: A list of package names to show. (List conmes from ggd_info metadata file)
    2) pks_dict: The ggd_info metadata file as a dictionary (To get verision and channel info)
    3) env_vars: A dictionary of environment variables. (Key = env_var name, value = path to file/dir)
    4) conda_list: A dictionary representing conda list output (from utils.get_conda_package_list())
    5) prefix: The prefix/conda environment to display information for. 
    6) prefix_set: True or False, whether the user set a prefix or not.
    """
    
    ## Create a 2d list for string formatting 
    formated_list = [["    Name","Pkg-Version","Pkg-Build","Channel","Environment-Variables"]]

    ## Iterate over each package in pkg_names
    for pkg in pkg_names:
        version = pkgs_dict[pkg]["version"] 
        assert version == conda_list[pkg]["version"]
        build = conda_list[pkg]["build"]
        channel = "ggd-"+pkgs_dict[pkg]["tags"]["ggd-channel"]
        assert channel == conda_list[pkg]["channel"]
        
        ## Get env_vars
        env_variables = []
        if ("ggd_"+pkg.replace("-","_").replace(".","_")+"_dir") in env_vars.keys():
            env_variables.append(" $ggd_"+pkg.replace("-","_").replace(".","_")+"_dir") 
        if ("ggd_"+pkg.replace("-","_").replace(".","_")+"_file") in env_vars.keys():
            env_variables.append(" $ggd_"+pkg.replace("-","_").replace(".","_")+"_file") 

        formated_list.append([pkg, version,build,channel,",".join(env_variables)]) 

    ## Print data pkg list
    print("\n\n# Packages in environment: {p}\n#".format(p=prefix))

    dash = '-' * 120
    for i in range(len(formated_list)):
        if i == 0:
          print(dash)
          print('{:<40s}{:>5s}{:>10s}{:>10s}{:>30s}'.format(formated_list[i][0],formated_list[i][1],formated_list[i][2],formated_list[i][3],formated_list[i][4]))
          print(dash)
        else:
          print('-> {:<40s}{:>5s}{:>10s}{:>15s}{:^60s}\n'.format(formated_list[i][0],formated_list[i][1],formated_list[i][2],formated_list[i][3],formated_list[i][4]))
    
    ## Print environment variables info 
    if prefix_set:
        print("# The environment variables are only available when you are using the '{p}' conda environment.".format(p=prefix))
    else:
        print("# To use the environment variables run `source activate base`")
        print("# You can see the available ggd data package environment variables by running `ggd show-env`\n")
        

def list_installed_packages(parser, args):
    """Main method of `ggd list` used to list installed ggd data package in user specified conda environment/prefix

    list_installed_packages
    =======================
    Main method of ggd list. This method will check and set the conda environment/prefix, check the ggd info metdata file
     get environmnet variables for ggd data packages in the user specified conda prefix, get the installed data packages 
     from conda info, filter results based on user specified pattern, and provide the information to the display function.
    """

    ## Check prefix
    CONDA_ROOT = args.prefix if args.prefix != None and prefix_in_conda(args.prefix) else conda_root()
    ggd_info_path = os.path.join(CONDA_ROOT,GGD_INFO)

    ## Check that the ggd info dir exists. If not, create it
    if not os.path.isdir(ggd_info_path):
        update_installed_pkg_metadata(prefix=CONDA_ROOT)

    ## Load json metadata data as dictionary
    metadata = load_json(os.path.join(CONDA_ROOT,GGD_INFO,METADATA))

    ## Get the environment variables
    env_vars = get_environment_variables(CONDA_ROOT)

    ## Get conda package list
    ggd_packages = get_conda_package_list(CONDA_ROOT)

    ## Get final package list 
    final_package_list = metadata["packages"].keys() 

    ## Check if there is a user defined pattern
    pat = args.pattern if args.pattern != None else None
    if args.pattern != None:
        matches = list(map(str,[re.search(".*"+args.pattern.lower()+".*",x).group() for x in metadata["packages"].keys() if re.search(args.pattern.lower(),x) != None]))
        if len(matches) < 1:
            #print("\n-> '{p}' did not match any installed data packages".format(p=args.pattern))
            sys.exit("\n-> '{p}' did not match any installed data packages".format(p=args.pattern))
            #sys.exit(0)
        else:
            final_package_list = matches

    ## Provide the results to stdout
    list_pkg_info(final_package_list, metadata["packages"], env_vars, ggd_packages, CONDA_ROOT, prefix_set = False if args.prefix == None else True )


