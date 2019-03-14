#-------------------------------------------------------------------------------------------------------------
## Import Statements
#-------------------------------------------------------------------------------------------------------------
from __future__ import print_function
import sys
import os
import glob
from .utils import conda_root
from .utils import get_species 
from .utils import get_builds
from .utils import validate_build
from .utils import get_ggd_channels
from .utils import get_channeldata_url
from .search import load_json_from_url, search_packages

SPECIES_LIST = get_species()

#-------------------------------------------------------------------------------------------------------------
## Argument Parser 
#-------------------------------------------------------------------------------------------------------------
def add_list_files(p):
    c = p.add_parser('list-files', help="List files for an installed ggd recipe")
    c.add_argument("-c", "--channel", default="genomics", choices=get_ggd_channels(), help="The ggd channel of the recipe to find. (Default = genomics)")
    c.add_argument("-s", "--species", help="(Optional) species recipe is for. Use '*' for any species", choices=SPECIES_LIST)
    c.add_argument("-g", "--genome-build", help="(Optional) genome build the recipe is for. Use '*' for any genome build.")
    c.add_argument("-v", "--version", help="(Optional) pattern to match the version of the file desired. Use '*' for any version")
    c.add_argument("-p", "--pattern", help="(Optional) pattern to match the name of the file desired. To list all files for a ggd package, do not use the -p option")
    c.add_argument("name", help="pattern to match recipe name(s)."+
        " Ex. `ggd list-files \"hg19-hello*\" -s \"Homo_sapiens\" -g \"hg19\" -p \"out*\"`")
    c.set_defaults(func=list_files)


#-------------------------------------------------------------------------------------------------------------
## Functions/Methods 
#-------------------------------------------------------------------------------------------------------------

# in_ggd_channel
# ==============
# Method used to identify in the desired pacakge is in the ggd-<channel>.
#  If it is the the species, build, and version is returned. 
#  If it is not, then a few alternative package names are provided
# 
# Parameters:
# ----------
# 1) ggd_recipe: The name of the ggd recipe
# 2) ggd_channel: The name of the ggd-channel to look in
# 
# Return:
# 1) species: The species for the ggd-recipe
# 2) build: The genome build for the ggd-recipe
# 3) version: The version of the ggd-recipe
def in_ggd_channel(ggd_recipe, ggd_channel):
    CHANNELDATA_URL = get_channeldata_url(ggd_channel)
    json_dict = load_json_from_url(CHANNELDATA_URL)
    package_list = [x[0] for x in search_packages(json_dict, ggd_recipe)]
    if ggd_recipe in package_list:
        species = json_dict["packages"][ggd_recipe]["identifiers"]["species"]
        build = json_dict["packages"][ggd_recipe]["identifiers"]["genome-build"]
        version = json_dict["packages"][ggd_recipe]["version"] 
        return(species,build,version)
    else:
        print("\n\t-> %s is not in the ggd-%s channel" %(ggd_recipe, ggd_channel))
        print("\t-> Similar recipes include: \n\t\t- {recipe}".format(recipe="\n\t\t- ".join(package_list[0:5])))
        sys.exit(1)


# list_files
# ==========
# Main method. Method used to list files for an installed ggd-recipe
def list_files(parser, args): 
    CONDA_ROOT = conda_root()
    name = args.name
    channeldata_species, channeldata_build, channeldata_version = in_ggd_channel(args.name, args.channel)
    species = args.species if args.species else channeldata_species
    build = args.genome_build if args.genome_build else channeldata_build
    if not validate_build(build, species):
        exit(1)
    version = args.version if args.version else "*"
    pattern = args.pattern if args.pattern else "*"
   
    path = os.path.join(CONDA_ROOT, "share", "ggd", species, build, name, version, pattern)
    files = glob.glob(path)
    if (files):
        print ("\n-> ", "\n-> ".join(files))
    else:
        print("\n\t-> No matching files found for %s" %args.name, file=sys.stderr)
        exit(1)
