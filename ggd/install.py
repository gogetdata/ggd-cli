#-------------------------------------------------------------------------------------------------------------
## Import Statements
#-------------------------------------------------------------------------------------------------------------
from __future__ import print_function 
import sys
import os
import subprocess as sp
import glob
from .check_recipe import conda_root
from .utils import get_ggd_channels
from .utils import get_channel_data
from .search import load_json, search_packages


#-------------------------------------------------------------------------------------------------------------
## Argument Parser
#-------------------------------------------------------------------------------------------------------------
def add_install(p):
	c = p.add_parser('install', help="install a data recipe from ggd")
	c.add_argument("name", help="the name of the recipe to install")
	c.add_argument("-c", "--channel", default="genomics", choices=get_ggd_channels(), help="The ggd channel the desired recipe is stored in. (Default = genomics)")
	c.set_defaults(func=install)

#-------------------------------------------------------------------------------------------------------------
## Functions/Methods
#-------------------------------------------------------------------------------------------------------------


# check_ggd_recipe
# ================
# Method to check if the ggd recipe exists. Uses searc_packages from search.py to 
#  search the ggd-channel json file. If the recipe exists within the json file,
#  the installation proceeds. If not, the instalation stops
def check_ggd_recipe(ggd_recipe,ggd_channel):
	CHANNEL_DATA = get_channel_data(ggd_channel)
	jdict = load_json(CHANNEL_DATA)
	package_list = [x[0] for x in search_packages(jdict, ggd_recipe)]
	if ggd_recipe in package_list:
		print("\n\t-> %s exists in ggd-%s" %(ggd_recipe,ggd_channel))
		return(jdict)
	else:
		print("\n\t-> '%s' was not found in ggd." %ggd_recipe)
		print("\t-> You can search for recipes using the ggd search tool: \n\t\t'ggd search -t %s'\n" %ggd_recipe)
		sys.exit()


# check_if_installed
# =================
# Method to check if the recipe has already been installed and is in 
#  the conda ggd storage path. If it is already installed the installation stops.
def check_if_installed(ggd_recipe,ggd_jdict):
	species = ggd_jdict["packages"][ggd_recipe]["identifiers"]["species"]
	build = ggd_jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
	version = ggd_jdict["packages"][ggd_recipe]["version"]

	CONDA_ROOT = conda_root()
	path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)
	recipe_exists = glob.glob(path)
	if recipe_exists:
		print("\n\t-> '%s' is already installed." %ggd_recipe)
		print("\t-> You can find %s here: %s" %(ggd_recipe,path))
		sys.exit()
	else:
		print("\n\t-> %s is not installed on your system" %ggd_recipe)
		return(False)
	

# check_conda_installation
# =======================
# Method used to check if the recipe has been installed using conda. 
def check_conda_installation(ggd_recipe):
	conda_package_list = sp.check_output(["conda", "list"])
	if conda_package_list.find(ggd_recipe) == -1:
		print("\n\t-> %s has not been installed by conda" %ggd_recipe)
		return(False)
	else:
		print("\n\t-> %s has been installed by conda on your system and must be uninstalled to proceed." %ggd_recipe)
		print("\t-> To reinstall run:\n\t\t ggd uninstall %s \n\t\t ggd install %s" %(ggd_recipe,ggd_recipe))


# check_S$_bucket
# ==============
# Method to check if the recipe is stored on the ggd S3 bucket. If so it installs from S3
# TODO: 
# Currently not implemented
def check_S3_bucket(ggd_recipe):
	print("S3 NOT implemented yet")
	return(False)
	## IF exists, install from here


# conda_install
# ============
# Method to install the recipe from the ggd-channel using conda
# TODO:
# Create ggd-genomics channel and add recipes. Current instalation DOES NOT 
#  work because ggd-genomics does not exist
def conda_install(ggd_recipe, ggd_channel):
	print("\n\t-> Installing %s" %ggd_recipe)
	try:
		sp.check_call(["conda", "install", "-c", "ggd-"+ggd_channel, "-y", ggd_recipe], stderr=sys.stderr, stdout=sys.stdout)
	except sp.CalledProcessError as e:
		sys.stderr.write("ERROR in install %s" %ggd_recipe)
		sys.exit(e.returncode)


# install
# ======
# Main method used to check installation and install the ggd recipe
def install(parser, args):
	print("\n\t-> Looking for %s in the 'ggd-%s' channel" %(args.name,args.channel))
	## Check if the recipe is in ggd
	ggd_jsonDict = check_ggd_recipe(args.name,args.channel)
	## Check if the recipe is already installed  
	if not check_if_installed(args.name,ggd_jsonDict):
		## Check if conda has it installed on the system 
		if not check_conda_installation(args.name):
			## Check S3 bucket
			if not check_S3_bucket(args.name):
				#if not installed from the S3 bucket install using  conda
				conda_install(args.name, args.channel)
			print("\n\t-> DONE")
				
