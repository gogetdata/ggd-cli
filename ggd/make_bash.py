import os
import shutil
import yaml
import subprocess as sp
# TODO: get this by querying the git repo.
species = ('Homo_sapiens', 'Mus_musculus', 'Canis_familiaris')


def conda_root():
    return sp.check_output(['conda', 'info', '--root']).strip()

def add_make_bash(p):
    c = p.add_parser('from_bash', help="make a new ggd/conda recipe give a bash script")
    c.add_argument("--species", help="species recipe is for", choices=species,
                   required=True)
    c.add_argument("--genome-build", help="genome-build the recipe is for",
                   required=True)
    c.add_argument("--authors", help="authors of the recipe", default=os.environ.get("USER", ""))
    c.add_argument("--version", help="version of data itself, e.g. dbsnp-127",
                   required=True)
    c.add_argument("--dependency", default=[], action="append",
        help="any software dependencies (in bioconda, conda-forge) or data-dependency (in ggd)" +
        ". May be as many times as needed.")
    c.add_argument("--extra-file", default=[], action="append",
        help="any files that the recipe creates that are not a *.gz and *.gz.tbi pair. May be used more than once")
    c.add_argument("--summary", help="a comment describing the recipe",
                   default="", required=True)
    c.add_argument("--keyword", help="a keyword to associate with the recipe." +
        " may be specified more that once.", action="append", default=[],
                   required=True)
    c.add_argument("name", help="name of recipe")
    c.add_argument("script", help="bash script that contains the commands that build the recipe")

    c.set_defaults(func=make_bash)


def make_bash(parser, args):

    name = args.name.replace(args.species, "").replace(args.genome_build, "").strip("- ")
    name = "{0}-{1}".format(args.genome_build, name)
    assert args.summary.strip() != ""

    try:
        os.makedirs(name)
    except OSError:
        shutil.rmtree(name)
        os.makedirs(name)

    recipe = {"build": {
                  "binary_relocation": False,
                  "detect_binary_files_with_prefix": False,
                  "number": 0},
              "extra": {
                  "authors": args.authors,
                  "genome-build": args.genome_build,
                  "species": args.species,
                  "keywords": args.keyword,
                  "extra-files": args.extra_file,
                  },
              "about": {"summary": args.summary},
              "package": {"name": name, "version": args.version},
              "requirements": {"build": args.dependency[:],
                               "run": args.dependency[:]},
              }

    with open(os.path.join(name, "meta.yaml"), "w") as fh:
        fh.write(yaml.dump(recipe, default_flow_style=False))

    CONDA_ROOT = conda_root()
    with open(os.path.join(name, "pre-link.sh"), "w") as fh:
        fh.write("""#!/bin/bash
set -eo pipefail -o nounset

CONDA_ROOT={CONDA_ROOT}

mkdir -p $CONDA_ROOT/share/ggd/{species}/{build}/
cd $CONDA_ROOT/share/ggd/{species}/{build}/

""".format(CONDA_ROOT=CONDA_ROOT,
           species=args.species,
           build=args.genome_build))

        fh.write(open(args.script).read())
        fh.write("echo 'SUCCESS!'\n")

    print("wrote output to %s/" % name)
    print("build with 'conda build %s/" % name)
