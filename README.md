# ggd-cli

The command-line interface to GGD. Build and check recipes.

[![Build Status](https://travis-ci.org/gogetdata/ggd-cli.svg?branch=master)](https://travis-ci.org/gogetdata/ggd-cli)

### Installation

This assumes that you have installed [anaconda](https://www.continuum.io/downloads) or at
least [conda](http://conda.pydata.org/docs/download.html)

To get the required software, use:

```
$ conda config --add channels bioconda
$ conda config --add channels conda-forge
$ conda install -y conda-build-all --channel conda-forge
$ conda install -y anaconda-client
$ conda install -y "gsort>=0.0.2" samtools htslib zlib check-sort-order
```

Finally:
```
$ pip install ggd
```

Then the `ggd` executable will be available.

## from-bash

Make a recipe from a bash script that is likely to pass the tests in ggd-recipes.

Most of the arguments are required. For example, we don't want a recipe to litter
the user-space with extra files so if the recipe downloads a `.zip`, and processes
the files inside of it, it should clean-up (`rm`) the .zip file upon completion.

```
usage: ggd from-bash [-h] -s
                     {Canis_familiaris,Homo_sapiens,Drosophila_melanogaster,Mus_musculus}
                     -g GENOME_BUILD [--authors AUTHORS] --version VERSION
                     [-d DEPENDENCY] [-e EXTRA_FILE] --summary SUMMARY -k
                     KEYWORD
                     name script

positional arguments:
  name                  name of recipe
  script                bash script that contains the commands that build the
                        recipe

optional arguments:
  -h, --help            show this help message and exit
  -s {Canis_familiaris,Homo_sapiens,Drosophila_melanogaster,Mus_musculus}, --species {Canis_familiaris,Homo_sapiens,Drosophila_melanogaster,Mus_musculus}
                        species recipe is for
  -g GENOME_BUILD, --genome-build GENOME_BUILD
                        genome-build the recipe is for
  --authors AUTHORS     authors of the recipe
  --version VERSION     version of data itself, e.g. dbsnp-127
  -d DEPENDENCY, --dependency DEPENDENCY
                        any software dependencies (in bioconda, conda-forge)
                        or data-dependency (in ggd). May be as many times as
                        needed.Using Anaconda API: https://api.anaconda.org
hg19-cosmic

install a recipe with: 
conda install -c ggd-dev --override-channels {recipe-name}

  -e EXTRA_FILE, --extra-file EXTRA_FILE
                        any files that the recipe creates that are not a *.gz
                        and *.gz.tbi pair. May be used more than once
  --summary SUMMARY     a comment describing the recipe
  -k KEYWORD, --keyword KEYWORD
                        a keyword to associate with the recipe. may be
                        specified more that once.
```

## check-recipe

Used after you make a new recipe, likely with the `ggd from-bash`. Running `ggd check-recipe` will
run the same checks as our testing framework. It will build and install the recipe.

It may miss dependencies if you have them installed on your system, but they are not specified in
the recipe. This will cause the recipe to fail when tested in our testing framework.

```
usage: ggd check-recipe /path/to/my/recipe/
```

## show-env

Shows the status of variables available in the conda environment. This is important as installation of a new ggd package will create a new environment variable to access data installed with the package, but will not activate that variable.

No arguments are required for show-env, but it will accept a regex pattern to filter results.

```
$ ggd show-env -p "ggd.*"

*****************************

Active environment variables:
> $ggd_hg19_cpg_islands

Inactive or out-of-date environment variables:
> $ggd_grch37_reference_genome
Using Anaconda API: https://api.anaconda.org
hg19-cosmic

install a recipe with: 
conda install -c ggd-dev --override-channels {recipe-name}

To activate inactive or out-of-date vars, run:
source activate root

*****************************
```

The environment variables store the location of the installation directory for the package. When activated, these variables can be used to simplify data access considerably, as shown below:

```
$ echo "$ggd_grch37_reference_genome"
/scratch/ucgd/lustre/u1072557/a2/share/ggd/Homo_sapiens/GRCh37/grch37-reference-genome

$ ls "$ggd_grch37_reference_genome"
hs37d5.fa  hs37d5.fa.fai
```

## list-files

Shows files that have been installed locally from a ggd recipe. Uses Python's glob.glob to list files, so pattern must use shell wildcards or literals, rather than regex.

```
$ ggd list-files -h
usage: ggd list-files [-h]
                      [-s {Canis_familiaris,Homo_sapiens,Drosophila_melanogaster,Mus_musculus}]
                      [-g GENOME_BUILD] [-v VERSION] [-p PATTERN]
                      name

positional arguments:
  name                  pattern to match recipe name(s). Ex. `ggd list-files
                        "hg19-hello*" -s "Homo_sapiens" -g "hg19" -p "out*"`

optional arguments:
  -h, --help            show this help message and exit
  -s {Canis_familiaris,Homo_sapiens,Drosophila_melanogaster,Mus_musculus}, --species {Canis_familiaris,Homo_sapiens,Drosophila_melanogaster,Mus_musculus}
                        species recipe is for
  -g GENOME_BUILD, --genome-build GENOME_BUILD
                        genome build the recipe is for
  -v VERSION, --version VERSION
                        pattern to match the version of the file desired
  -p PATTERN, --pattern PATTERN
                        pattern to match the name of the file desired
```

```
usage: ggd list-files "hg19-hello*" -s "Homo_sapiens" -g "hg19" -p "out*" -v "1"
```

## search

Allows user to search available ggd recipes. Performs a two-part search, first checking a locally-managed copy of the ggd-recipes repository and then going to the ggd-dev channel to verify that only fully tested packages are reported. The `keyword` arguments, if provided, are matched against the keywords stored in the meta.yaml `extra` section.

```
$ ggd search -h
usage: ggd search [-h]
                  [-s {Canis_familiaris,Homo_sapiens,Drosophila_melanogaster,Mus_musculus}]
                  [-g GENOME_BUILD] [-k KEYWORD]
                  name

positional arguments:
  name                  pattern to match the name of the recipe desired. Ex.
                        `ggd search "hg19*" -s "Homo_sapiens" -g "hg19"`

optional arguments:
  -h, --help            show this help message and exit
  -s {Canis_familiaris,Homo_sapiens,Drosophila_melanogaster,Mus_musculus}, --species {Canis_familiaris,Homo_sapiens,Drosophila_melanogaster,Mus_musculus}
                        species recipe is for
  -g GENOME_BUILD, --genome-build GENOME_BUILD
                        genome build the recipe is for
  -k KEYWORD, --keyword KEYWORD
                        keywords to narrow search. Repeat argument to use
                        multiple keywords
```

```
usage: ggd search "hg19-c*" -s "Homo_sapiens" -g "hg19" -k "cosmic"
```

`search` also helps the user out by giving the command needed to install a package (results below from above example):

```
Using Anaconda API: https://api.anaconda.org
hg19-cosmic

install a recipe with: 
conda install -c ggd-dev --override-channels {recipe-name}
```
