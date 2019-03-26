from __future__ import print_function
import os
import shutil
import yaml
import subprocess as sp
from .utils import get_species 
from .utils import get_ggd_channels
from .utils import get_conda_env 
from collections import OrderedDict
from .utils import check_output, conda_root

SPECIES_LIST = [x.encode('ascii') for x in get_species()]
CHANNEL_LIST = [x.encode('ascii') for x in get_ggd_channels()]


def add_make_bash(p):
    c = p.add_parser('make-recipe', help="make a new ggd/conda recipe give a bash script")
    c.add_argument("-c", "--channel", help="the ggd channel to use. (Default = genomics)", choices=[x.decode('ascii') for x in CHANNEL_LIST],
                    default='genomics')
    c.add_argument("-d", "--dependency", default=[], action="append",
                    help="any software dependencies (in bioconda, conda-forge) or data-dependency (in ggd)" +
                    ". May be as many times as needed.")
    c.add_argument("-e", "--extra-file", default=[], action="append",
                    help="any files that the recipe creates that are not a *.gz and *.gz.tbi pair. May be used more than once")
    c.add_argument("-p", "--platform", default="noarch", help="Whether to use noarch as the platfrom or the system platform. If set to 'none' the system platform will be used. (Default = noarch. Noarch means no architecture and is platform agnostic.)",
                    choices=["noarch", "none"])
    c2 = c.add_argument_group("required arguments")
    c2.add_argument("-s", "--species", help="species recipe is for", choices=[x.decode('ascii') for x in SPECIES_LIST],
                    required=True)
    c2.add_argument("-g", "--genome-build", help="genome-build the recipe is for",
                    required=True)
    c2.add_argument("--authors", help="authors of the recipe", default=os.environ.get("USER", ""))
    c2.add_argument("-gv", "--ggd_version", help="The version of the ggd package. (First time package = 1, updated package > 1)",
                    required=True)
    c2.add_argument("-dv", "--data_version", help="The version of the data (itself) being downloaded and processed (EX: dbsnp-127)", 
                    required=True)
    c2.add_argument("--summary", help="a comment describing the recipe",
                default="", required=True)
    c2.add_argument("-k", "--keyword", help="a keyword to associate with the recipe." +
                    " may be specified more that once.", action="append", default=[],
                    required=True)
    c.add_argument("name", help="name of recipe")
    c.add_argument("script", help="bash script that contains the commands that build the recipe")

    c.set_defaults(func=make_bash)


def make_bash(parser, args):

    name = args.name.replace(args.species, "").replace(args.genome_build, "").strip("- ")
    name = "{0}-{1}-v{2}".format(args.genome_build, name, args.ggd_version).lower()
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

    if args.platform == "noarch":
        yml1 = {"build": {
                      "noarch": "generic",
                      "binary_relocation": False,
                      "detect_binary_files_with_prefix": False,
                      "number": 0}}
    else:
        yml1 = {"build": {
                      "binary_relocation": False,
                      "detect_binary_files_with_prefix": False,
                      "number": 0}}
    yml2 = {"extra": {
                    "authors": args.authors,
                    "extra-files": args.extra_file,
                }}
    yml3 = {"package": {"name": name, "version": args.ggd_version}}
    yml4 = {"requirements": {"build": deps[:],
                    "run": deps[:]}}
    yml5 = { "source": {"path": "."}}

    yml6 = {"about": {
                    "identifiers": {
                    "species": args.species,
                    "genome-build": args.genome_build
                },
                    "keywords": args.keyword,
                    "summary": args.summary,
                    "tags": {
                        "data-version": args.data_version,
                        "ggd-channel": args.channel
                    },
                }}


    with open(os.path.join(name, "meta.yaml"), "a") as fh:
        fh.write(yaml.dump(yml1, default_flow_style=False))
        fh.write(yaml.dump(yml2, default_flow_style=False))
        fh.write(yaml.dump(yml3, default_flow_style=False))
        fh.write(yaml.dump(yml4, default_flow_style=False))
        fh.write(yaml.dump(yml5, default_flow_style=False))
        fh.write(yaml.dump(yml6, default_flow_style=False))

    with open(os.path.join(name, "post-link.sh"), "w") as fh:
        fh.write("""#!/bin/bash
set -eo pipefail -o nounset

if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
    export CONDA_ROOT=$(conda info --root)
    env_dir=$CONDA_ROOT
    export RECIPE_DIR=$CONDA_ROOT/share/ggd/{species}/{build}/{name}/{version}
elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
    export CONDA_ROOT=$(conda info --root)
    env_dir=$CONDA_ROOT
    export RECIPE_DIR=$CONDA_ROOT/share/ggd/{species}/{build}/{name}/{version}
else
    env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
    export CONDA_ROOT=$env_dir
    export RECIPE_DIR=$env_dir/share/ggd/{species}/{build}/{name}/{version}
fi

PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

if [ -d $RECIPE_DIR ]; then
    rm -r $RECIPE_DIR
fi

mkdir -p $RECIPE_DIR

recipe_env_name="ggd_{name}"
recipe_env_name="$(echo "$recipe_env_name" | sed 's/-/_/g')"

activate_dir="$env_dir/etc/conda/activate.d"
deactivate_dir="$env_dir/etc/conda/deactivate.d"

mkdir -p $activate_dir
mkdir -p $deactivate_dir

echo "export $recipe_env_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
echo "unset $recipe_env_name">> $deactivate_dir/env_vars.sh

(cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

cd $RECIPE_DIR

## Iterate over new files and replace file name with data package name and data version  
for f in *; do
    ext="${ext_string}"
    filename="{filename_string}"
    (mv $f "{name}.$ext")
done

echo 'Recipe successfully built!'
""".format(species=args.species,
           name=name,
           build=args.genome_build,
           version=args.ggd_version,
           ext_string="{f#*.}", ## Bash get extention. (.bed, .bed.gz, etc.) 
           filename_string="{f%%.*}"))

    with open(os.path.join(name, "recipe.sh"), "w") as fh:
        fh.write("#!/bin/sh\nset -eo pipefail -o nounset\n")
        fh.write(open(args.script).read())

    print("\n\t-> Wrote output to %s/" % name)
    print("\n\t-> To test that the recipe is working, and before pushing the new recipe to gogetdata/ggd-recipes, please run: \n\t\t$ ggd check-recipe %s/"  % name)
