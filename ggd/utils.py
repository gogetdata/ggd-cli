from __future__ import print_function
import os

import sys
import glob
from git import Repo

LOCAL_REPO_DIR = os.getenv("GGD_LOCAL", os.path.expanduser("~/.config/"))
RECIPE_REPO_DIR = os.path.join(LOCAL_REPO_DIR, "ggd-recipes")
GITHUB_URL = "https://github.com/gogetdata/ggd-recipes.git"
METADATA_REPO_DIR = os.path.join(LOCAL_REPO_DIR, "ggd-metadata")
METADATA_GITHUB_URL = "https://github.com/gogetdata/ggd-metadata"

def get_species():
    update_local_repo()
    genomes_dir = os.path.join(RECIPE_REPO_DIR, "genomes")
    return os.listdir(genomes_dir)

## Should be called after get_species
def get_ggd_channels():
	recipe_dir = os.path.join(RECIPE_REPO_DIR, "recipes")
	return os.listdir(recipe_dir)

def get_channel_data(ggd_channel):
	update_metadata_local_repo()
	channeldata_path = os.path.join(METADATA_REPO_DIR, "channeldata", ggd_channel, "channeldata.json")
	return (channeldata_path)

def get_channeldata_url(ggd_channel):
	return(os.path.join("https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/channeldata", ggd_channel,
			"channeldata.json"))

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

def update_metadata_local_repo():
    if not os.path.isdir(LOCAL_REPO_DIR):
        os.makedirs(LOCAL_REPO_DIR)
    if not os.path.isdir(METADATA_REPO_DIR):
        Repo.clone_from(METADAT_GITHUB_URL, METADATA_REPO_DIR)
    Repo(METADATA_REPO_DIR).remotes.origin.pull()

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
