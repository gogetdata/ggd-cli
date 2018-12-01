#-------------------------------------------------------------------------------------------------------------
## Import Statements
#-------------------------------------------------------------------------------------------------------------
from __future__ import print_function 
import sys
import os
import subprocess as sp
import glob
import shutil
from .check_recipe import conda_root
from .utils import get_ggd_channels
from .utils import get_channel_data
from .search import load_json, search_packages



#-------------------------------------------------------------------------------------------------------------
## Argument Parser 
#-------------------------------------------------------------------------------------------------------------
def add_uninstall(p):
	c = p.add_parser('uninstall', help="uninstall a ggd data recipe")
	c.add_argument("name", help="the name of the recipe to uninstall")
	c.add_argument("-c", "--channel", default="genomics", choices=get_ggd_channels(), help="The ggd channel of the recipe to uninstall. (Default = genomics)")
	c.set_defaults(func=uninstall)


#-------------------------------------------------------------------------------------------------------------
## Functions/Methods 
#-------------------------------------------------------------------------------------------------------------


# get_channeldata
# ===============
# Method to get the channel data and check if the recipe is within that channel.
#  This method is to identify the files installed during installation, but that 
#  won't be removed by normal uninstalling. These files will be removed by the 
#  check_if_installed() method if it is found within the channeldata.json file
def get_channeldata(ggd_recipe,ggd_channel):
	CHANNEL_DATA = get_channel_data(ggd_channel)
	jdict = load_json(CHANNEL_DATA)
	package_list = [x[0] for x in search_packages(jdict,ggd_recipe)]
	if ggd_recipe in package_list:
		return(jdict)
	else:
		print("\n\t-> %s is not in the ggd-%s channel." %(ggd_recipe,ggd_channel))
		print("\t-> %s will still be uninstalled, however, the packages will remain on your system." %ggd_recipe)
		print("\t-> To remove completely, provide the correct ggd-channel. Current ggd-channel = %s" %ggd_channel)
		return({})
		

# check_if_installed
# =================
# Method used to remove extra files created during recipe installation, but that are not 
#  removed during normal uninstallation. 
# This method depends on the get_channeldata method. If the recipe is not found in the 
#  channeldata.json file the extra files will not be removed. 
def check_if_installed(ggd_recipe,ggd_jdict):
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
	else:
		print("\n\t-> %s is not in the ggd recipe storage" %ggd_recipe)


# remove_from_condaroot
# ====================
# Method used to remove the recipe's extra files created during installation, but that are not removed 
#  when uninstalled. 
def remove_from_condaroot(ggd_recipe,version):
	find_list = sp.check_output(['find', conda_root(), '-name', ggd_recipe+"-"+str(version)+"*"]).strip().split("\n")
	print("\n\t-> Deleteing %d items of %s version %s from your conda root" %(len(find_list),ggd_recipe,version))
	for path in find_list:
		if os.path.isdir(path):
			shutil.rmtree(path)
		else:
			os.remove(path)


# check_conda_installation
# ========================
# Method used to check if the recipe has been installed with conda. If so, it uses conda to uninstall the recipe
def check_conda_installation(ggd_recipe):
	conda_package_list = sp.check_output(["conda", "list"])
	if conda_package_list.find(ggd_recipe) == -1:
		print("\n\t-> %s is NOT installed on your system" %ggd_recipe)
	else:
		print("\n\t-> %s is installed by conda on your system" %ggd_recipe)
		conda_uninstall(ggd_recipe)


# conda_uninstall
# ===============
# Method used to uninstall ggd recipe using conda
def conda_uninstall(ggd_recipe):
	print("\n\t-> Uninstalling %s" %ggd_recipe)
	try:
		sp.check_call(["conda", "uninstall", "-y", ggd_recipe], stderr=sys.stderr, stdout=sys.stdout)
	except sp.CalledProcessError as e:
		sys.stderr.write("ERROR in uninstall %s" %ggd_recipe)
		sys.exit(e.returncode)


# uninstall
# =========
# Main method used to check if the recipe is installed, uninstall the recipe, and remove extra recipe files
def uninstall(parser, args):
	print("\n\t-> Checking for instalation of %s" %args.name)
	## Get the channeldata.json file in dictionary form
	ggd_jsonDict = get_channeldata(args.name,args.channel)
	## Check if insatlled through conda
	check_conda_installation(args.name)
	## Check if the recipe is in file system   
	if len(ggd_jsonDict) > 0:
		check_if_installed(args.name,ggd_jsonDict)
	else:
		print("\n\t-> Skipping pakage removal from system step")

	print("\n\t-> DONE")
				

