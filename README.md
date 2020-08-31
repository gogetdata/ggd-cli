![GoGetData](https://github.com/gogetdata/gogetdata.github.io/blob/master/_images/GoGetData_name_logo.png)

ggd-cli: The command line interface for gogetdata
=================================================

[![Anaconda-Server Badge](https://anaconda.org/bioconda/ggd/badges/installer/conda.svg)](https://anaconda.org/bioconda/ggd/)
[![CircleCI](https://circleci.com/gh/gogetdata/ggd-cli/tree/master.svg?style=shield)](https://circleci.com/gh/gogetdata/ggd-cli/tree/master)
[![Anaconda-Server Badge](https://anaconda.org/bioconda/ggd/badges/downloads.svg)](https://anaconda.org/bioconda/ggd)
![Anaconda-Server Badge](https://anaconda.org/bioconda/ggd/badges/license.svg)
![latest-Release Badge](https://img.shields.io/github/v/release/gogetdata/ggd-cli?label=latest%20release%2Fversion)



The command-line interface to Go Get Data (GGD). 

Search, and install genomic data packages. Build and check new ggd data packages. 

ggd provides easy access to processed genomic data. It removes the difficulties and complexities with finding and processing the data sets and annotations germane to your experiments and/or analyses. You can quickly and easily search and install data package using ggd. ggd also offers tools to easily create and contribute data packages to ggd. (From more information see the [ggd docs](https://gogetdata.github.io/index.html#).

**The documentation for ggd is available** [here](https://gogetdata.github.io/index.html#) and contains detailed information about the ggd system, including installing ggd, using ggd, available data packages, etc. The information below provides a quick overview of using ggd, but we encourage you to visit the [ggd docs](https://gogetdata.github.io/index.html#) for detailed information and questions you may have.

You can also visit the [ggd docs: quick-start](https://gogetdata.github.io/quick-start.html) page to start using ggd quickly. 

You can request a new data recipe be added to GGD by filling out the [GGD Recipe Request](https://forms.gle/3WEWgGGeh7ohAjcJA) Form.

## Setting up ggd

Assuming that you have already installed an *ananconda* distribution on your system, you can run the following commands to set up ggd. 

> **_NOTE:_** If you have not installed an anaconda distribution on your system please install it. We suggest using [miniconda](https://conda.io/en/latest/miniconda.html) 

1) Adding the required conda channels including ggd specific channels:

- ggd data packages are hosted on the Anaconda cloud through the ggd-genomics channel. You will need to add this channel to your configured conda channels. You will also need to add the channels that have the software dependencies for building these data packages. Run the following commands:

```
$ conda config --add channels defaults
$ conda config --add channels ggd-genomics
$ conda config --add channels bioconda
$ conda config --add channels conda-forge
```

2a) Installing ggd:

- The ggd cli can be installed by conda, and this is the recommended way to do it.  

```
$ conda install -c bioconda ggd
```

2b) Installing ggd (Not using Conda)

- ggd can also be installed through github. Conda is required and it is still recommended that you install with conda. Below is an additional option you can use to install ggd.

```
$ conda install -y --file https://raw.githubusercontent.com/gogetdata/ggd-cli/master/requirements.txt

$ pip install -U git+git://github.com/gogetdata/ggd-cli
```

Now that ggd is installed on your system you should be able to run `ggd`. Test that ggd has been installed by running:

```
$ ggd -h
```


## ggd commands

### ggd search 

You can search for ggd data packages using the `ggd search` tool. You can also search for packages on the 
[ggd docs: available packages](https://gogetdata.github.io/recipes.html) page. 

If you need the GRCh38 reference genome you can use ggd to search and install it. Simply use ggd to search for 
the desired data package:

```
$ ggd search reference genome
```

You can further filter the results using additional options with `ggd search`. Run `ggd search -h` to see all options.

For more information about ggd's search tool see: [ggd docs: ggd search](https://gogetdata.github.io/ggd-search.html)


### ggd install

You can install any ggd data package using the `ggd install` tool. 

If you need the GRCh38 reference genome, and you have used `ggd search reference genome` to identify which reference-genome data package you want to install, you can use ggd to install that data package.

```
$ ggd install grch38-reference-genome-ensembl-v1
```

The output from this command will provide the locations of where the files were installed, as well as an environment variable that you can use to quickly access the files.

> **_NOTE:_** If you want to move the files PLEASE make a copy and move the copy. Moving the original files from the location ggd installed them will remove ggd's ability to manage those data files

For more information about ggd's install tool see: [ggd docs: ggd install](https://gogetdata.github.io/install.html)


### ggd uninstall

You can uninstall any ggd data package that has previously been installed by ggd on your system using `ggd uninstall`. 

The ggd uninstall tool provides file and system-wide handling for ggd package. Problems may occur if you do not use the `ggd uninstall` tool to uninstall and remove the un-needed data packages.

If you no longer need or want the GRCh38 reference genome installed from above you can use ggd to remove it from your system. 

```
ggd uninstall grch38-reference-genome-ensembl-v1

```

For more information about ggd's uninstall tool see: [ggd docs: ggd uninstall](https://gogetdata.github.io/uninstall.html)


### Additional ggd tools for file management 

ggd has additional tools available to find, access, and use the data install by ggd. 

These tools include:

`ggd list`

- get a list of installed data files

`ggd get-files`

- get files that have been installed locally from a ggd recipe.

`ggd pkg-info`

- Show the information for a specific data package installed by ggd. 

`ggd show-env`

- Shows the status of variables available in the conda environment. This is important as the installation of a new ggd package will create a new environment variable to access data installed with the package, but will not always activate that variable.
- The environment variables store the location of the installation directory for the package. When activated, these variables can be used to simplify data access.

You can get more information about each of these tools on the ggd docs pages. 
[ggd list](https://gogetdata.github.io/list.html), [ggd get-files](https://gogetdata.github.io/list-file.html), [ggd pkg-info](https://gogetdata.github.io/pkg-info.html), 
[ggd show-env](https://gogetdata.github.io/show-env.html).


## Prefix

GGD utilizes conda environments. To facilitate the use of different conda environments, some ggd commands use a `--prefix` argument. This `--prefix` argument
can be used to install, list, and even access data files in a different conda environment then the one you are actively working in.

The prefix capability of ggd allows user to install all data from ggd into a specific conda environment, and access that data all without having to be in 
that conda environment. This helps to reduce duplicate data installs on your system, as well as provide a means to access data in any environment you are using
as long as ggd is installed in that environment. 


## Contributing to ggd 

We intend ggd to become a widely used genomics data management system. In this effort we encourage and invite everyone to contribute to the ggd recipe repository. 
ggd provides multiple tools to create and check data recipes that can be added to ggd. If you have data you would like to be hosted on ggd, whether your own or 
from somewhere else, please either use ggd  to make the recipe or request a new data recipe be added. 

For more information about contributing data recipes/packages to ggd please see [ggd docs: contribute](https://gogetdata.github.io/contribute.html)

Two scripts are available to assist you in making and checking recipes 

## ggd make-recipe

Make a recipe from a bash script that is likely to pass the tests in ggd-recipes.

Most of the arguments in `ggd make-recipe` are required. Any recipe created should be able to clean up 
after it has finished processing the data fiels. For example, we don't want a recipe to litter
the user-space with extra files so if the recipe downloads a `.zip`, and processes
the files inside of it, it should clean-up (`rm`) the .zip file upon completion.


You can run `ggd make-recipe -h` to get all the parameters needed to make a recipe. You can also see them
at [ggd docs: ggd make-recipe](https://gogetdata.github.io/make-recipe.html).

To make a recipe you need to start with a bash script that downloads and processes the desired  data. For example, if you wanted to 
make a recipe for the GRCh37 reference genome hosted by 1000 Genomes your bash script would look something like this:

*recipe.sh*
```
# get reference file from 1000 genomes ftp site
wget --quiet http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz

# unzip the reference
bgzip -fd hs37d5.fa.gz 

# index the reference
samtools faidx hs37d5.fa
```

With this bash script, you can now create a ggd recipe using `ggd make-recipe`.

```
ggd make-recipe \
    -s Homo_sapiens \
    -g GRCh37 \
    --author <your name> \
    --package-version 1 \
    --data-version phase2_reference \
    --data-provider 1000G \
    -cb "NA" \
    --summary 'GRCh37 reference genome from 1000 genomes' \
    -k ref \
    -k reference \
    --name reference-genome \
    recipe.sh
```

Running `ggd make-recipe` will create a new "directory" *recipe* with multiple processing files. For the GRCh37 reference genome recipe made above 
the directory/recipe will be called "grch37-reference-genome-1000g-v1"

For more information about ggd's make-recipe tool see: [ggd docs: ggd make-recipe](https://gogetdata.github.io/make-recipe.html).

## ggd check-recipe

Use `ggd check-recipe` after you have created a new recipe with `ggd make-recipe`. Running `ggd check-recipe` will run the same 
checks as our testing framework. It will build and install the recipe.

It may miss dependencies if you have them installed on your system, but they are not specified in
the recipe. This will cause the recipe to fail when tested in our testing framework.

To check the grch37-reference-genome recipe created above run:

```
$ ggd check-recipe grch37-reference-genome-1000g-v1
```

For more information about ggd's check-recipe tools see: [ggd docs: ggd check-recipe](https://gogetdata.github.io/check-recipe.html).
