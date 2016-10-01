from __future__ import print_function
import sys
import os
import glob
from .make_bash import conda_root
from .utils import get_species 
from .utils import get_builds
from .utils import validate_build

SPECIES_LIST = get_species()

def add_list_files(p):
    c = p.add_parser('list-files', help="list files in ggd for a given recipe")
    c.add_argument("-s", "--species", help="species recipe is for", choices=SPECIES_LIST)
    c.add_argument("-g", "--genome-build", help="genome build the recipe is for")
    c.add_argument("-p", "--pattern", help="regular expression pattern to match the name of the file desired")
    c.add_argument("name", help="pattern to match recipe name(s)."+
        " Ex. `ggd list-files \"hg19-hello*\" -s \"Homo_sapiens\" -g \"hg19\" -p \"out*\"`")
    c.set_defaults(func=list_files)

# TODO need to make this find in a case-insensitive manner
def list_files(parser, args): 
    CONDA_ROOT = conda_root()
    name = args.name
    species = args.species if args.species else "*"
    build = args.genome_build if args.genome_build else "*"
    if not validate_build(build, species):
        exit(1)
    pattern = args.pattern if args.pattern else "*"
   
    path = os.path.join(CONDA_ROOT, "share", "ggd", species, build, name, pattern)
    files = glob.glob(path)
    if (files):
        print ("\n".join(files))
    else:
        print("No matching files found", file=sys.stderr)
        exit(1)
