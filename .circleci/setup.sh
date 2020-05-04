#!/bin/bash

set -exo pipefail

WORKSPACE=$(pwd)

# Set path
echo "export PATH=$WORKSPACE/anaconda/bin:$PATH" >> $BASH_ENV
source $BASH_ENV

## Passed from .circleci/config.yml (Only 2 or 3 permited)
pythonversion=$1
if (( $pythonversion != 2 && $pythonversion != 3 ))
then
    echo -e "\nERROR: Python 2 or 3 designation required. Python version $pythonversion was supplied. Please correct and run again\n"
    exit 1  
fi 

# setup conda and dependencies 
if [[ ! -d $WORKSPACE/anaconda ]]; then
    mkdir -p $WORKSPACE


    # step 1: download and install anaconda
    if [[ $OSTYPE == darwin* ]]; then
        tag="MacOSX"
        tag2="darwin"
    elif [[ $OSTYPE == linux* ]]; then
        tag="Linux"
        tag2="linux"
    else
        echo "Unsupported OS: $OSTYPE"
        exit 1
    fi  

    curl -L -O https://repo.continuum.io/miniconda/Miniconda$pythonversion-latest-$tag-x86_64.sh
    sudo bash Miniconda$pythonversion-latest-$tag-x86_64.sh -b -p $WORKSPACE/anaconda/
    sudo chown -R $USER $WORKSPACE/anaconda/
    curl -Lo $WORKSPACE/anaconda/bin/check-sort-order https://github.com/gogetdata/ggd-utils/releases/download/v0.0.6/check-sort-order-$tag2\_amd64

    chmod +x $WORKSPACE/anaconda/bin/check-sort-order
    mkdir -p $WORKSPACE/anaconda/conda-bld/$tag-64

    # step 2: setup channels
    conda config --system --add channels defaults
    conda config --system --add channels bioconda
    conda config --system --add channels conda-forge
    conda config --system --add channels ggd-genomics

    ## Add strict priority 
    conda config --system --add channel_priority: strict

    # step 3: install ggd requirements 
    conda install -y --file requirements.txt 


    # step 5: cleanup
    conda clean -y --all

    # Add local channel as highest priority
    mkdir -p $WORKSPACE/miniconda/conda-bld/{noarch,linux-64,osx-64}
    conda index $WORKSPACE/miniconda/conda-bld
    conda config --system --add channels file://$WORKSPACE/miniconda/conda-bld

fi

conda config --get

ls $WORKSPACE/miniconda/conda-bld
ls $WORKSPACE/miniconda/conda-bld/noarch


