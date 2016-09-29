from __future__ import print_function
import sys
import os
import glob
import json
from subprocess import check_output
from subprocess import call
from .utils import get_species 
from .utils import get_builds
from .utils import validate_build
from .utils import RECIPE_REPO_DIR
from .check_recipe import _to_str

SPECIES_LIST = get_species()

def add_search(p):
    c = p.add_parser('search', help="search conda's available recipes. ")
    c.add_argument("-s", "--species", help="species recipe is for", choices=SPECIES_LIST)
    c.add_argument("-g", "--genome-build", help="genome build the recipe is for")
    c.add_argument("name", help="pattern to match the name of the recipe desired. Ex. `ggd search \"hg19*\" -s \"Homo_sapiens\" -g \"hg19\"`")
    c.set_defaults(func=search)


def search(parser, args):   
    name = args.name
    species = args.species if args.species else "*"
    build = args.genome_build if args.genome_build else "*"

    if not validate_build(build, species):
        exit(1)

    path = os.path.join(RECIPE_REPO_DIR, "recipes", species, build, name)
    files = glob.glob(path)
    for i in range(len(files)):
        files[i] = os.path.split(files[i])[1]

    conda_json = _to_str(check_output(["conda", "search", "-c",
		"ggd-alpha", "--override-channels", "--json", name]))

    matches = json.loads(conda_json)
    conda_recipes = []
    for matches_key in matches:
        for match_data in matches[matches_key]:
            for match_data_key in match_data:
                if match_data_key == "name":
                    conda_recipes.append(match_data[match_data_key])
    for filename in files:
        if filename not in conda_recipes:
            files.remove(filename)

    if (files):
        print ("\n".join(files))
        print("\ninstall a recipe with: \nconda install -c ggd-alpha --override-channels {recipe-name}")
    else:
        print("No matching recipes found", file=sys.stderr)
        exit(1)
