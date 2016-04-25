# ggd-cli
The command-line interface to GGD

### Installation

```
$ pip install ggd
```

Then the `ggd` executable will be available.

## from\_bash

Make a recipe from a bash script that is likely to pass the tests in ggd-recipes.

Most of the arguments are required. For example, we don't want a recipe to litter
the user-space with extra files so if the recipe downloads a `.zip`, and processes
the files inside of it, it should clean-up (`rm`) the .zip file upon completion.

```
usage: ggd from_bash [-h] --species
                     {Homo_sapiens,Mus_musculus,Canis_familiaris}
                     --genome-build GENOME_BUILD [--authors AUTHORS] --version
                     VERSION [--dependency DEPENDENCY]
                     [--extra-file EXTRA_FILE] --summary SUMMARY --keyword
                     KEYWORD
                     name script

positional arguments:
  name                  name of recipe
  script                bash script that contains the commands that build the
                        recipe

optional arguments:
  -h, --help            show this help message and exit
  --species {Homo_sapiens,Mus_musculus,Canis_familiaris}
                        species recipe is for
  --genome-build GENOME_BUILD
                        genome-build the recipe is for
  --authors AUTHORS     authors of the recipe
  --version VERSION     version of data itself, e.g. dbsnp-127
  --dependency DEPENDENCY
                        any software dependencies (in bioconda, conda-forge)
                        or data-dependency (in ggd). May be as many times as
                        needed.
  --extra-file EXTRA_FILE
                        any files that the recipe creates that are not a *.gz
                        and *.gz.tbi pair. May be used more than once
  --summary SUMMARY     a comment describing the recipe
  --keyword KEYWORD     a keyword to associate with the recipe. may be
                        specified more that once.

```
