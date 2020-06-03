from __future__ import print_function

import os

from .utils import get_builds, get_ggd_channels, get_species

SPECIES_LIST = sorted(get_species())
GENOME_BUILDS = sorted(get_builds("*"))
CHANNEL_LIST = [x.encode("ascii") for x in get_ggd_channels()]
GENOMIC_COORDINATE_LIST = [
    "0-based-inclusive",
    "0-based-exclusive",
    "1-based-inclusive",
    "1-based-exclusive",
    "NA",
]


def add_make_bash(p):
    c = p.add_parser(
        "make-recipe",
        help="Make a new ggd data recipe with a user developed bash script",
        description="Make a ggd data recipe from a bash script",
    )
    c.add_argument(
        "-c",
        "--channel",
        help="the ggd channel to use. (Default = genomics)",
        choices=[x.decode("ascii") for x in CHANNEL_LIST],
        default="genomics",
    )
    c.add_argument(
        "-d",
        "--dependency",
        default=[],
        action="append",
        help="any software dependencies (in bioconda, conda-forge) or data-dependency (in ggd)"
        + ". May be as many times as needed.",
    )
    c.add_argument(
        "-e",
        "--extra-file",
        default=[],
        action="append",
        help="any files that the recipe creates that are not a *.gz and *.gz.tbi pair or *.fa and *.fai pair. May be used more than once",
    )
    c.add_argument(
        "-p",
        "--platform",
        default="noarch",
        help="Whether to use noarch as the platfrom or the system platform. If set to 'none' the system platform will be used. (Default = noarch. Noarch means no architecture and is platform agnostic.)",
        choices=["noarch", "none"],
    )
    c2 = c.add_argument_group("required arguments")
    c2.add_argument(
        "-s",
        "--species",
        help="The species recipe is for",
        choices=[str(x) for x in SPECIES_LIST],
        required=True,
    )
    c2.add_argument(
        "-g",
        "--genome-build",
        choices=[str(x) for x in GENOME_BUILDS],
        help="The genome build the recipe is for",
        required=True,
    )
    c2.add_argument(
        "--authors",
        help="The author(s) of the data recipe being created, (This recipe)",
        default=os.environ.get("USER", ""),
    )
    c2.add_argument(
        "-pv",
        "--package-version",
        help="The version of the ggd package. (First time package = 1, updated package > 1)",
        required=True,
    )
    c2.add_argument(
        "-dv",
        "--data-version",
        help="The version of the data (itself) being downloaded and processed (EX: dbsnp-127)" +
        " If there is no data version apparent we recommend you use the date associated with the files" +
        " or something else that can uniquely identify the 'version' of the data",
        required=True,
    )
    c2.add_argument(
        "-dp",
        "--data-provider",
        required=True,
        help="The data provider where the data was accessed. (Example: UCSC, Ensembl, gnomAD, etc.)",
    )
    c2.add_argument(
        "--summary",
        help="A detailed comment describing the recipe",
        default="",
        required=True,
    )
    c2.add_argument(
        "-k",
        "--keyword",
        help="A keyword to associate with the recipe."
        + " May be specified more that once."
        + " Please add enough keywords to better describe and distinguish the recipe",
        action="append",
        default=[],
        required=True,
    )
    c2.add_argument(
        "-cb",
        "--coordinate-base",
        required=True,
        choices=GENOMIC_COORDINATE_LIST,
        help="The genomic coordinate basing for the file(s) in the recipe. That is, the coordianances start at genomic coordinate 0 or 1,"
        + " and the end coordinate is either inclusive (everything up to and including the end coordinate) or exlcusive (everthing up to but not including the end coordinate)"
        + " Files that do not have coordiante basing, like fasta files, specify NA for not applicable.",
    )
    c2.add_argument(
        "-n",
        "--name",
        help="The sub-name of the recipe being created. (e.g. cpg-islands, pfam-domains, gaps, etc.)"
        + " This will not be the final name of the recipe, but will describe what data the recipe gets",
        required=True,
    )
    c2.add_argument(
        "script",
        help="bash script that contains the commands to obtain and process the data",
    )

    c.set_defaults(func=make_bash)


def make_bash(parser, args):

    import shutil
    import sys
    import yaml

    name = (
        args.name.replace(args.species, "")
        .replace(args.genome_build, "")
        .strip("- ")
        .strip()
    )
    data_provider = (
        args.data_provider.replace(args.species, "")
        .replace(args.genome_build, "")
        .strip("- ")
        .strip()
        .lower()
    )
    name = "{0}-{1}-{2}-v{3}".format(
        args.genome_build, name, data_provider, args.package_version
    ).lower()
    name = name.replace("_", "-")
    assert name.strip() != "{0}--{1}-v{2}".format(
        args.genome_build, data_provider, args.package_version
    ), "The recipe name is required"  ## test for missing name
    assert name.strip() != "{0}-{1}--v{2}".format(
        args.genome_build, args.name.lower(), args.package_version
    ), "The data provider is required"  ## test for missing name
    assert (
        args.summary.strip() != ""
    ), "Please provide a thorough summary of the data package"
    print("\n:ggd:make-recipe: Name of recipe: {0}-{1}-{2}-v{3}\n".format(
            args.genome_build.lower(),
            args.name.lower(),
            data_provider.lower(),
            args.package_version.lower(),
        )
    )
    assert name == "{0}-{1}-{2}-v{3}".format(
        args.genome_build.lower(),
        args.name.lower(),
        data_provider.lower(),
        args.package_version.lower(),
    ), "The recipe name is not formated correctly"

    wildcards = [
        "?",
        "*",
        "[",
        "]",
        "{",
        "}",
        "!",
        "\\",
        "(",
        ")",
        ".",
        "+",
        "^",
        "$",
        "|",
    ]
    for x in wildcards:
        assert (
            x not in name
        ), '\n\n\t"{}" wildcard is not allowed in the recipe name. Please rename the recipe. \n\tRecipe name = {} \n\tList of wildcards not allowed: {}'.format(
            x, name, " ".join(wildcards)
        )

    try:
        os.makedirs(name)
    except OSError:
        shutil.rmtree(name)
        os.makedirs(name)

    from .check_recipe import _check_build

    print(":ggd:make-recipe: checking", args.genome_build)
    _check_build(args.species, args.genome_build)

    try:
        recipe_bash = open(args.script).read()
    except IOError as e:
        print(e)
        sys.exit(1)

    # use these to automate inserting some dependencies.
    look = {
        "tabix": "htslib",
        "bgzip": "htslib",
        "perl": "perl",
        "gsort": "gsort",
        "samtools": "samtools",
        "gzip": "zlib",
        "zcat": "zlib",
        "gunzip": "zlib",
        "vt": "vt",
    }
    deps = sorted(
        set(
            [look.get(p, p) for p in args.dependency]
            + [look[prog] for prog in look if prog in recipe_bash]
        )
    )



    from .search import load_json
    from .utils import get_channel_data

    ## Get a list of ggd packages
    ggd_packages = set()
    for channel in CHANNEL_LIST:
        channel = channel.decode("utf-8") if not isinstance(channel,str) else channel
        json_dict = load_json(get_channel_data(channel))
        ggd_packages.update(json_dict["packages"].keys())

    ## Get non-ggd dependencies 
    non_ggd_deps = [x for x in deps if x not in ggd_packages]


    extra_files = []
    for f in args.extra_file:
        flist = f.strip().split(".")
        flist[0] = name
        extra_files.append(".".join(flist))

    ## Check coordinates
    assert (
        args.coordinate_base in GENOMIC_COORDINATE_LIST
    ), "{c} is not an acceptable genomic coordinate base".format(
        c=args.coordinate_base
    )
    # ("Please provide a genomic coordinate base from the follow list: {}".format(", ".join(GENOMIC_COORDINATE_LIST)))

    ## Check data version
    assert (
        args.data_version
    ), "Please provide the version of the data this recipe curates"
    assert (
        args.data_version.strip != ""
    ), "Please provide the version of the data this recipe curates"

    if args.platform == "noarch":
        yml1 = {
            "build": {
                "noarch": "generic",
                "binary_relocation": False,
                "detect_binary_files_with_prefix": False,
                "number": 0,
            }
        }
    else:
        yml1 = {
            "build": {
                "binary_relocation": False,
                "detect_binary_files_with_prefix": False,
                "number": 0,
            }
        }
    yml2 = {"extra": {"authors": args.authors, "extra-files": extra_files,}}
    yml3 = {"package": {"name": name, "version": args.package_version}}
    yml4 = {"requirements": {"build": non_ggd_deps[:], "run": deps[:]}}
    yml5 = {"source": {"path": "."}}
    yml6 = {
        "about": {
            "identifiers": {"species": args.species, "genome-build": args.genome_build},
            "keywords": args.keyword,
            "summary": args.summary,
            "tags": {
                "genomic-coordinate-base": args.coordinate_base.strip(),
                "data-version": args.data_version.strip(),
                "data-provider": args.data_provider.strip(),
                "file-type": [],
                "final-files": [],
                "final-file-sizes": {},
                "ggd-channel": args.channel,
            },
        }
    }

    ## Write output with specific key order
    with open(os.path.join(name, "meta.yaml"), "a") as fh:
        fh.write(yaml.dump(yml1, default_flow_style=False))
        fh.write(yaml.dump(yml2, default_flow_style=False))
        fh.write(yaml.dump(yml3, default_flow_style=False))
        fh.write(yaml.dump(yml4, default_flow_style=False))
        fh.write(yaml.dump(yml5, default_flow_style=False))
        fh.write(yaml.dump(yml6, default_flow_style=False))

    with open(os.path.join(name, "post-link.sh"), "w") as fh:
        fh.write(
            """#!/bin/bash
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


PKG_DIR=`find "$CONDA_SOURCE_PREFIX/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`


if [ -d $RECIPE_DIR ]; then
    rm -r $RECIPE_DIR
fi

mkdir -p $RECIPE_DIR

(cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

cd $RECIPE_DIR

## Iterate over new files and replace file name with data package name and data version  
for f in *; do
    ext="${ext_string}"
    filename="{filename_string}"
    if [[ ! -f "{name}.$ext" ]]  
    then
        (mv $f "{name}.$ext")
    fi  
done

## Add environment variables 
#### File
if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
then
    recipe_env_file_name="ggd_{name}_file"
    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g' | sed 's/\./_/g')"
    file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
then
    indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
    if [[ ! -z "$indexed_file" ]] ## If index file exists
    then
        recipe_env_file_name="ggd_{name}_file"
        recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g' | sed 's/\./_/g')"
        file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
    fi
fi 

#### Dir
recipe_env_dir_name="ggd_{name}_dir"
recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g' | sed 's/\./_/g')"

activate_dir="$env_dir/etc/conda/activate.d"
deactivate_dir="$env_dir/etc/conda/deactivate.d"

mkdir -p $activate_dir
mkdir -p $deactivate_dir

echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

#### File
    ## If the file env variable exists, set the env file var
if [[ ! -z "${file_env_var}" ]] 
then
    echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
    echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
fi
    

echo 'Recipe successfully built!'
""".format(
                species=args.species,
                name=name,
                build=args.genome_build,
                version=args.package_version,
                ext_string="{f#*.}",  ## Bash get extention. (.bed, .bed.gz, etc.)
                filename_string="{f%%.*}",
                file_env_var="{recipe_env_file_name:-}",
            )
        )

    with open(os.path.join(name, "recipe.sh"), "w") as fh:
        fh.write("#!/bin/sh\nset -eo pipefail -o nounset\n")
        fh.write(open(args.script).read())

    ## Create empty checksum file
    open(os.path.join(name, "checksums_file.txt"), "a").close()

    print("\n:ggd:make-recipe: Wrote output to %s/" % name)
    print(
        "\n:ggd:make-recipe: To test that the recipe is working, and before pushing the new recipe to gogetdata/ggd-recipes, please run: \n\t$ ggd check-recipe %s/"
        % name
    )

    return True
