from __future__ import print_function
import os

import sys
import glob
from git import Repo

LOCAL_REPO_DIR = os.getenv("GGD_LOCAL", os.path.expanduser("~/.config/"))
RECIPE_REPO_DIR = os.path.join(LOCAL_REPO_DIR, "ggd-recipes")
GITHUB_URL = "https://github.com/gogetdata/ggd-recipes.git"

def get_species():
    update_local_repo()
    genomes_dir = os.path.join(RECIPE_REPO_DIR, "genomes")
    return os.listdir(genomes_dir)

'''**************
TODO:
Hard Coded
NEED TO FIX
**************'''
## Recipe dir is flattened. Subdirs = channels
def get_ggd_channels():
	update_local_repo()
	#recipe_dir = os.path.join(RECIPE_REPO_DIR, "recipes")
	recipe_dir = os.path.join("/uufs/chpc.utah.edu/common/home/u1138933/QuinlanLab/ggd/post-link-recipes/ggd-recipes","recipes")
	return os.listdir(recipe_dir)

'''**************
TODO:
Hard Coded
NEED TO FIX
**************'''
def get_channel_data(ggd_channel):
	update_local_repo()
	#channeldata_path = os.path.join(RECIPE_REPO_DIR, "channeldata", ggd_channel, "channeldata.json")
	channeldata_path = os.path.join("/uufs/chpc.utah.edu/common/home/u1138933/QuinlanLab/ggd/ggd-recipes/", "channeldata", ggd_channel,"ggd-7recipes-channeldata.json")
	return (channeldata_path)

def get_builds(species):
    update_local_repo()
    species_dir = os.path.join(RECIPE_REPO_DIR, "genomes", species)

    if species == "*":
        paths = glob.glob(species_dir)
        builds = []
        for path in paths:
            builds.extend(os.listdir(path))
        return builds
    else:
        if os.path.isdir(species_dir):
            return os.listdir(species_dir)


def update_local_repo():
    if not os.path.isdir(LOCAL_REPO_DIR):
        os.makedirs(LOCAL_REPO_DIR)
    if not os.path.isdir(RECIPE_REPO_DIR):
        Repo.clone_from(GITHUB_URL, RECIPE_REPO_DIR)
    Repo(RECIPE_REPO_DIR).remotes.origin.pull()

def validate_build(build, species):
    if build != "*":
        builds_list = get_builds(species)
        if not builds_list or build not in builds_list:
            if species != "*":
                print("Unknown build '%s' for species '%s'" % (build, species), file=sys.stderr)
            else:
                print("Unknown build '%s'" % (build), file=sys.stderr)
            if (builds_list):
                print("Available builds: '%s'" % ("', '".join(builds_list)), file=sys.stderr)
            return False
    return True
   

if __name__ == "__main__":
    import doctest
    doctest.testmod()
