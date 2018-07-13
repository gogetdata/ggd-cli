from __future__ import print_function
import os
import shutil
import yaml
import subprocess as sp
from .utils import get_species 
from .show_env import get_conda_env 

SPECIES_LIST = [x.encode('ascii') for x in get_species()]

from .check_recipe import check_output
from .check_recipe import conda_root

def add_make_bash(p):
    c = p.add_parser('from-bash', help="make a new ggd/conda recipe give a bash script")
    c.add_argument("-s", "--species", help="species recipe is for", choices=[x.decode('ascii') for x in SPECIES_LIST],
                   required=True)
    c.add_argument("-g", "--genome-build", help="genome-build the recipe is for",
                   required=True)
    c.add_argument("--authors", help="authors of the recipe", default=os.environ.get("USER", ""))
    c.add_argument("--version", help="version of data itself, e.g. dbsnp-127",
                   required=True)
    c.add_argument("-d", "--dependency", default=[], action="append",
        help="any software dependencies (in bioconda, conda-forge) or data-dependency (in ggd)" +
        ". May be as many times as needed.")
    c.add_argument("-e", "--extra-file", default=[], action="append",
        help="any files that the recipe creates that are not a *.gz and *.gz.tbi pair. May be used more than once")
    c.add_argument("--summary", help="a comment describing the recipe",
                   default="", required=True)
    c.add_argument("-k", "--keyword", help="a keyword to associate with the recipe." +
        " may be specified more that once.", action="append", default=[],
                   required=True)
    c.add_argument("name", help="name of recipe")
    c.add_argument("script", help="bash script that contains the commands that build the recipe")

    c.set_defaults(func=make_bash)


def make_bash(parser, args):

    name = args.name.replace(args.species, "").replace(args.genome_build, "").strip("- ")
    name = "{0}-{1}".format(args.genome_build, name).lower()
    assert args.summary.strip() != ""

    try:
        os.makedirs(name)
    except OSError:
        shutil.rmtree(name)
        os.makedirs(name)

    from .check_recipe import _check_build
    print("checking", args.genome_build)
    _check_build(args.species, args.genome_build)

    recipe_bash = open(args.script).read()
    # use these to automate inserting some dependencies.
    look = {'tabix': 'htslib', 'bgzip': 'htslib', 'perl': 'perl',
            'gsort': 'gsort',
            'samtools': 'samtools', 'gzip': 'zlib',
            'zcat': 'zlib', 'gunzip': 'zlib', 'vt': 'vt'}
    deps = sorted(
              set([look.get(p, p) for p in args.dependency] +
                  [look[prog] for prog in look if prog in recipe_bash]))

    recipe = {"build": {
                  "noarch": "generic",
                  "binary_relocation": False,
                  "detect_binary_files_with_prefix": False,
                  "number": 0},
              "source": {"path": "."},
              "extra": {
                  "authors": args.authors,
                  "genome-build": args.genome_build,
                  "species": args.species,
                  "keywords": args.keyword,
                  "extra-files": args.extra_file,
                  },
              "about": {"summary": args.summary},
              "package": {"name": name, "version": args.version},
              "requirements": {"build": deps[:],
                               "run": deps[:]},
              }

    with open(os.path.join(name, "meta.yaml"), "w") as fh:
        fh.write(yaml.dump(recipe, default_flow_style=False))

    with open(os.path.join(name, "pre-link.sh"), "w") as fh:
        fh.write("""#!/bin/bash
set -eo pipefail -o nounset

export CONDA_ROOT=$(conda info --root)

pushd `dirname $0` > /dev/null
HERE=`pwd`
popd > /dev/null

export RECIPE_DIR=$CONDA_ROOT/share/ggd/{species}/{build}/{name}/{version}

if [ -d $RECIPE_DIR ]; then
    rm -r $RECIPE_DIR
fi

mkdir -p $RECIPE_DIR

recipe_env_name="ggd_{name}"
recipe_env_name="$(echo "$recipe_env_name" | sed 's/-/_/g')"

env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")

activate_dir="$env_dir/etc/conda/activate.d"
deactivate_dir="$env_dir/etc/conda/deactivate.d"

mkdir -p $activate_dir
mkdir -p $deactivate_dir

echo "export $recipe_env_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
echo "unset $recipe_env_name">> $deactivate_dir/env_vars.sh
ggd show-env

(cd $RECIPE_DIR && bash $HERE/../info/recipe/recipe.sh)

echo 'SUCCESS!'
""".format(species=args.species,
           name=name,
           build=args.genome_build,
           version=args.version))

    with open(os.path.join(name, "recipe.sh"), "w") as fh:
        fh.write("#!/bin/bash\nset -eo pipefail -o nounset\n")
        fh.write(open(args.script).read())

    print("wrote output to %s/" % name)
    print("build with 'conda build %s/" % name)
