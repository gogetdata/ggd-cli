import sys
import os
import glob
from .make_bash import conda_root
from .utils import get_species 
from .utils import get_builds

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
    if build != "*":
        builds_list = [x.encode('ascii') for x in get_builds(species)]
        if build not in builds_list:
            if species != "*":
                sys.stderr.write("Unknown build " + "'" + build + "'" + " for " + species + '\n')
            else:
                sys.stderr.write("Unknown build " + "'" + build + "'" + '\n')
            sys.stderr.write("Available builds: " + ", ".join(builds_list) + "\n")
            exit(1)
    pattern = args.pattern if args.pattern else "*"
   
    path = os.path.join(CONDA_ROOT, "share/ggd", species, build, name, pattern)
    files = glob.glob(path)
    if (files):
        print ("\n".join(files))
    else:
        sys.stderr.write("No matching files found\n")
        exit(1)
