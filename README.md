# ggd-cli

The command-line interface to Go Get Data (GGD). 

Search, and install genomic and omic data packages. Build and check new ggd data packages. 

ggd provides easy access to processed omic data. It removes the difficulties and complexities with finding and processing the data sets and annotations germane to your experiments and/or analyses. You can quickly and easily search and install data package using ggd. ggd also offers tools to easily create and contribute data packages to ggd. (From more information see the [ggd docs](https://gogetdata.github.io/index.html#).

**The documentation for ggd is available** [here](https://gogetdata.github.io/index.html#) and contains detailed information about the ggd system, including installing ggd, using ggd, available data packages, etc. The information below provides a quick start to using ggd, but we encourage you to visit the [ggd docs](https://gogetdata.github.io/index.html#) for detailed information and questions you may have.


## ggd tools

### ggd search 

You can search for ggd data packages using the `ggd search` tool. You can also search for packages on the 
[ggd docs: available packages](https://gogetdata.github.io/recipes.html) page. 

If you need the GRCh38 reference genome you can use ggd to search and install it. Simply use ggd to search for 
the desired data package:

```
$ ggd search -t reference genome
```

You can further filter the results using additional options with `ggd search`. Run `ggd search -h` to see all options.

For more information about ggd's search tool see: [ggd docs: ggd search](https://gogetdata.github.io/ggd-search.html)


### ggd install

You can install any ggd data package using the `ggd install` tool. 

If you need the GRCh38 reference genome, and you have used `ggd search -t reference genome` to identify which reference-genome data package you want to install, you can use ggd to install that data package.

```
$ ggd install grch38-reference-genome
```

The output from this command will provide the locations of where the files were installed, as well as an environment variable that you can use to quickly access the files.

**NOTE: If you want to move the files PLEASE make a copy and move the copy. Moving the original files from the location ggd installed them will remove ggd's ability to manage those data files.**

For more information about ggd's install tool see: [ggd docs: ggd install](https://gogetdata.github.io/ggd-install.html)


### ggd uninstall

You can uninstall any ggd data package that has previously been installed by ggd on your system using `ggd uninstall`. 

The ggd uninstall tool provides file and system-wide handling for ggd package. Problems may occur if you do not use the `ggd uninstall` tool to uninstall and remove the un-needed data packages.

If you no longer needed or wanted the GRCh38 reference genome installed from above you can use ggd to remove it from your system. 

```
ggd uninstall grch38-reference-genome

```

For more information about ggd's uninstall tool see: [ggd docs: ggd uninstall](https://gogetdata.github.io/uninstall.html)


### Aditional ggd tools for file management 

ggd has additional tools available to find, access, and use the data install by ggd. 

These tools include:

`ggd list-files`
- Shows files that have been installed locally from a ggd recipe.

`ggd pkg-info`
- Show the information for a specific data package installed by ggd. 

`ggd show-env`
- Shows the status of variables available in the conda environment. This is important as the installation of a new ggd package will create a new environment variable to access data installed with the package, but will not always activate that variable.
- The environment variables store the location of the installation directory for the package. When activated, these variables can be used to simplify data access.

You can get more information about each of these tools on the ggd docs pages. 
[ggd list-files](https://gogetdata.github.io/list-file.html), [ggd pkg-info](https://gogetdata.github.io/pkg-info.html), 
[ggd show-env](https://gogetdata.github.io/show-env.html).


## Contributing to ggd 

We intend ggd to become a widely used omics data management system. If this effort we encourage and invite everyone to contribute to the ggd recipe repository. ggd provides multiple tools to create and check data recipes that can be added to ggd. If you have data you would like to be hosted on ggd, whether your own or from somewhere else, please either use ggd  to make the recipe or request it in the Issue section. 

For more information about contributing data recipes/packages to ggd please see [ggd docs: contribute](https://gogetdata.github.io/contribute.html)

Two scripts are available to assist you in making and checking recipes 

## ggd make-recipe

Make a recipe from a bash script that is likely to pass the tests in ggd-recipes.

Most of the arguments are required. For example, we don't want a recipe to litter
the user-space with extra files so if the recipe downloads a `.zip`, and processes
the files inside of it, it should clean-up (`rm`) the .zip file upon completion.


You can run `ggd make-recipe -h` to get all the parameters needed to make a recipe. You can also see them
at [ggd docs: ggd make-recipe](https://gogetdata.github.io/make-recipe.html).

To make a recipe you need to start with a bash script that downloads and processes the desired omic data. For example, if you wanted to make a recipe for the GRCh37 reference genome hosted by 1000 Genomes your bash script would look something like this:

recipe.sh
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
$ ggd make-recipe \
    -s Homo_sapiens \
    -g hg38 \
    --author me \
    --ggd_version 1 \
    --data_version 06-Mar-2014 \
    --summary 'RepeatMasker track from UCSC' \
    -k rmsk -k region \
    repeatmasker \
    recipe.sh
```

Running `ggd make-recipe` will create a new "directory" *recipe* with multiple processing files. For the GRCh37 reference genome recipe made above the directory/recipe will be called "grch37-reference-genome"

For more information about ggd's make-recipe tool see: [ggd docs: ggd make-recipe](https://gogetdata.github.io/make-recipe.html).

## ggd check-recipe

Use `ggd check-recipe` after you have created a new recipe with `ggd make-recipe`. Running `ggd check-recipe` will run the same checks as our testing framework. It will build and install the recipe.

It may miss dependencies if you have them installed on your system, but they are not specified in
the recipe. This will cause the recipe to fail when tested in our testing framework.

To check the grch37-reference-genome recipe created above run:

```
$ ggd check-recipe grch37-reference-genome
```

For more information about ggd's check-recipe tools see: [ggd docs: ggd check-recipe](https://gogetdata.github.io/check-recipe.html).
