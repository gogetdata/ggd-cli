import sys
import os
import glob
from .make_bash import conda_root
from .utils import get_species 

SPECIES_LIST = [x.encode('ascii') for x in get_species()]

def add_list_files(p):
    c = p.add_parser('list-files', help="list files in ggd for a given recipe")
    c.add_argument("--species", help="species recipe is for", choices=SPECIES_LIST)
    c.add_argument("--genome-build", help="genome build the recipe is for")
    c.add_argument("--pattern", help="regular expression pattern to match the name of the file desired")
    c.add_argument("name", help="name of recipe")
    c.set_defaults(func=list_files)


def list_files(parser, args):   
    CONDA_ROOT = conda_root()
    name = args.name
    species = args.species if args.species else "*"
    build = args.genome_build if args.genome_build else "*"
    pattern = args.pattern if args.pattern else "*"
   
    path = os.path.join(CONDA_ROOT, "share/ggd", species, build, name, pattern)
    files = glob.glob(path)
    if (files):
        print ("\n".join(files))
    else:
        sys.stderr.write("No matching files found\n")
        exit(1)


#get_builds -> optional arg (species)
