from __future__ import print_function
import os
import sys
import subprocess as sp
import pytest
import yaml
import tempfile
import requests
import argparse
import json
import re
import time
from copy import deepcopy
from argparse import Namespace
from argparse import ArgumentParser
import glob
import contextlib
import tarfile
from helpers import CreateRecipe
from ggd import utils
from ggd import check_recipe
from ggd import uninstall
from ggd import show_env

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO


#---------------------------------------------------------------------------------------------------------
## Test Label
#---------------------------------------------------------------------------------------------------------

TEST_LABEL = "ggd-check-recipe-test"

#---------------------------------------------------------------------------------------------------------
## IO redirection
#---------------------------------------------------------------------------------------------------------

## Create a redirect_stdout that works for python 2 and 3. (Similar to contextlib.redirect_stdout in python 3)
@contextlib.contextmanager
def redirect_stdout(target):
    original = sys.stdout
    sys.stdout = target
    yield
    sys.stdout = original

## Create a redirect_stderr that works for python 2 and 3. (Similar to contextlib.redirect_stderr in python 3)
@contextlib.contextmanager
def redirect_stderr(target):
    original = sys.stderr
    sys.stderr = target
    yield
    sys.stderr = original



#-----------------------------------------------------------------------------------------------------------------------
# Unit test for ggd check-recipe
#-----------------------------------------------------------------------------------------------------------------------

def test_list_files():
    """
    Test thate list_files function properly returns the list of files
    """

    ## Use the CreateRecipe function to create a temporary directory to test list files with 
    dir1 = CreateRecipe(
    """
    dir1:
        file1.bed: |
            * This is a fake bed file

            wget https//www.a.fake.bed.file.bed

            gsort a.fake.bed.file.bed
            bgzip a.fake.bed.file.bed
            tabix a.fkae.bed.file.bed.gz
        file1.bed.gz: |
            * A bgzip bed file 
            
            Some ziped bytes 

        file1.bed.gz.tbi: |
            * A bgziped and tabixed bed file

            Some tabix bytes
    """, from_string=True)

    dir1.write_recipes()
    dir1_path = os.path.join(dir1.recipe_dirs["dir1"])
    files = check_recipe.list_files(dir1_path)
    assert len(files) == 3
    for file_tuple in files:
        file_path = file_tuple[0]
        assert re.search(r"\bfile1.bed$",file_path) or re.search(r"\bfile1.bed.gz$",file_path) or re.search(r"\bfile1.bed.gz.tbi$",file_path) 
        ## Modify file
        time.sleep(1)
        with open(file_path, "a") as fp:
            fp.write("Modified")

    ## Test for modified file
    modfiles = check_recipe.list_files(dir1_path)
    assert len(modfiles) == 3
    for i, file_tuple in enumerate(modfiles):
        file_modified_time = file_tuple[1]
        assert file_modified_time > files[i][1]
        ## Remove file path
        os.remove(file_tuple[0])

    ## Test empty dir
    files = check_recipe.list_files(dir1_path)
    assert len(files) == 0


def test_conda_platform():
    """
    Test that the conda_platform function correctly returns the system platform 
    """

    platform = check_recipe.conda_platform()
    out = sys.platform
    if "linux" in out:
        assert "linux" in platform
    elif "darwin" in out:
        assert "osx" in platform
    else:
        assert out in platform


def test__build_use_system_platform():
    """
    test the _build function is affected by a bad order of the meta.yaml keys
    """

    ## testing-hg38-gaps-v1 recipe as of 3/27/2019 (noarch: generic removed from meta.yaml)
    recipe = CreateRecipe(
    """
    trial-hg38-gaps-v1:
        meta.yaml: |
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              number: 0
            extra:
              authors: mjc 
              extra-files: []
            package:
              name: trial-hg38-gaps-v1
              version: '1' 
            requirements:
              build:
              - gsort
              - htslib
              - zlib
              run:
              - gsort
              - htslib
              - zlib
            source:
              path: .
            about:
              identifiers:
                genome-build: hg38
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: hg38 Assembly gaps from USCS
              tags:
                data-version: 11-Mar-2019
                ggd-channel: genomics

        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg38/hg38.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg38/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > gaps.bed.gz

            tabix gaps.bed.gz 
       
        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --ooot)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            fi

            PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

            if [ -d $RECIPE_DIR ]; then
                rm -r $RECIPE_DIR
            fi

            mkdir -p $RECIPE_DIR

            (cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

            cd $RECIPE_DIR

            ## Iterate over new files and replace file name with data package name and data version  
            for f in *; do
                ext="${f#*.}"
                filename="{f%%.*}"
                (mv $f "trial-hg38-gaps-v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_trial-hg38-gaps-v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_trial-hg38-gaps-v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_trial-hg38-gaps-v1_dir"
            recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g')"

            activate_dir="$env_dir/etc/conda/activate.d"
            deactivate_dir="$env_dir/etc/conda/deactivate.d"

            mkdir -p $activate_dir
            mkdir -p $deactivate_dir

            echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
            echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

            #### File
            if [[ ! -z "${recipe_env_file_name:-}" ]] ## If the file env variable exists, set the env file var
            then
                echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
                echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
            fi

            echo 'Recipe successfully built!'
    """, from_string=True)

    recipe.write_recipes()

    ## Test a normal run of _build()
    recipe_dir_path = recipe.recipe_dirs["trial-hg38-gaps-v1"] 
    yaml_file = yaml.load(open(os.path.join(recipe_dir_path, "meta.yaml")))
    
    tarball_file_path = check_recipe._build(recipe_dir_path,yaml_file)

    platform = sys.platform

    if "linux" in platform:
        assert "linux" in tarball_file_path
    elif "darwin" in platform:
        assert "osx" in tarball_file_path
    else:
        print("built using platform: %s" %platform)
        os.remove(tarball_file_path)
        assert False

    ## Remove the platform specific build
    os.remove(tarball_file_path)

    
def test__build_bad_yaml_key_order():
    """
    test the _build function is affected by a bad order of the meta.yaml keys
    """

    ## testing-hg38-gaps-v1 recipe as of 3/27/2019 (meta.yaml keys reordered)
    recipe = CreateRecipe(
    """
    trial-hg38-gaps-v1:
        meta.yaml: |
            about:
              identifiers:
                genome-build: hg38
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: hg38 Assembly gaps from USCS
              tags:
                data-version: 11-Mar-2019
                ggd-channel: genomics
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              noarch: generic
              number: 0
            package:
              name: trial-hg38-gaps-v1
              version: '1' 
            requirements:
              build:
              - gsort
              - htslib
              - zlib
              run:
              - gsort
              - htslib
              - zlib
            source:
              path: .
            extra:
              authors: mjc 
              extra-files: []
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg38/hg38.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg38/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > gaps.bed.gz

            tabix gaps.bed.gz 
        
        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            fi

            PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

            if [ -d $RECIPE_DIR ]; then
                rm -r $RECIPE_DIR
            fi

            mkdir -p $RECIPE_DIR

            (cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

            cd $RECIPE_DIR

            ## Iterate over new files and replace file name with data package name and data version  
            for f in *; do
                ext="${f#*.}"
                filename="{f%%.*}"
                (mv $f "trial-hg38-gaps-v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_trial-hg38-gaps-v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_trial-hg38-gaps-v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_trial-hg38-gaps-v1_dir"
            recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g')"

            activate_dir="$env_dir/etc/conda/activate.d"
            deactivate_dir="$env_dir/etc/conda/deactivate.d"

            mkdir -p $activate_dir
            mkdir -p $deactivate_dir

            echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
            echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

            #### File
            if [[ ! -z "${recipe_env_file_name:-}" ]] ## If the file env variable exists, set the env file var
            then
                echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
                echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
            fi


            echo 'Recipe successfully built!'
    """, from_string=True)

    recipe.write_recipes()
    recipe_dir_path = recipe.recipe_dirs["trial-hg38-gaps-v1"] 
    yaml_file = yaml.load(open(os.path.join(recipe_dir_path, "meta.yaml")))
    
    ## Test conda build fail for bad yaml key order
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe._build(recipe_dir_path,yaml_file)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("5") ## Check that the exit code is 1


def test__build_ggd_requirments_removed_on_bad_build():
    """
    test the _build function is able to remove ggd requirements when the build fails
    """

    ## testing-hg38-gaps-v1 recipe as of 3/27/2019 (meta.yaml keys reordered)
    recipe = CreateRecipe(
    """
    trial-hg38-gaps-v1:
        meta.yaml: |
            about:
              identifiers:
                genome-build: hg38
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: hg38 Assembly gaps from USCS
              tags:
                data-version: 11-Mar-2019
                ggd-channel: genomics
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              noarch: generic
              number: 0
            package:
              name: trial-hg38-gaps-v1
              version: '1' 
            requirements:
              build:
              - hg19-gaps-v1
              - gsort
              - htslib
              - zlib
              run:
              - hg19-gaps-v1
              - gsort
              - htslib
              - zlib
            source:
              path: .
            extra:
              authors: mjc 
              extra-files: []
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg38/hg38.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg38/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > gaps.bed.gz

            tabix gaps.bed.gz 
        
        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            fi

            PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

            if [ -d $RECIPE_DIR ]; then
                rm -r $RECIPE_DIR
            fi

            mkdir -p $RECIPE_DIR

            (cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

            cd $RECIPE_DIR

            ## Iterate over new files and replace file name with data package name and data version  
            for f in *; do
                ext="${f#*.}"
                filename="{f%%.*}"
                (mv $f "trial-hg38-gaps-v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_trial-hg38-gaps-v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_trial-hg38-gaps-v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_trial-hg38-gaps-v1_dir"
            recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g')"

            activate_dir="$env_dir/etc/conda/activate.d"
            deactivate_dir="$env_dir/etc/conda/deactivate.d"

            mkdir -p $activate_dir
            mkdir -p $deactivate_dir

            echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
            echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

            #### File
            if [[ ! -z "${recipe_env_file_name:-}" ]] ## If the file env variable exists, set the env file var
            then
                echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
                echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
            fi


            echo 'Recipe successfully built!'
    """, from_string=True)

    recipe.write_recipes()
    recipe_dir_path = recipe.recipe_dirs["trial-hg38-gaps-v1"] 
    yaml_file = yaml.load(open(os.path.join(recipe_dir_path, "meta.yaml")))
    
    ## Test conda build fail for bad yaml key order
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe._build(recipe_dir_path,yaml_file)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("5") ## Check that the exit code is 1
    
 
## A global variable for a successfull tarball file created using the ggd _build function
pytest.global_tarball_testing_file = ""
pytest.global_ggd_recipe_path = ""

def test__build_normal_run():
    """
    test the _build function properly builds a ggd recipe into a ggd pocakge using conda build
    """

    ## testing-hg38-gaps-v1 recipe as of 3/27/2019
    recipe = CreateRecipe(
    """
    trial-hg38-gaps-v1:
        meta.yaml: |
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              noarch: generic
              number: 0
            extra:
              authors: mjc 
              extra-files: []
            package:
              name: trial-hg38-gaps-v1
              version: '1' 
            requirements:
              build:
              - gsort
              - htslib
              - zlib
              run:
              - gsort
              - htslib
              - zlib
            source:
              path: .
            about:
              identifiers:
                genome-build: hg38
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: hg38 Assembly gaps from USCS
              tags:
                data-version: 11-Mar-2019
                ggd-channel: genomics
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg38/hg38.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg38/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > gaps.bed.gz

            tabix gaps.bed.gz 
        
        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1
            fi

            PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

            if [ -d $RECIPE_DIR ]; then
                rm -r $RECIPE_DIR
            fi

            mkdir -p $RECIPE_DIR

            (cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

            cd $RECIPE_DIR

            ## Iterate over new files and replace file name with data package name and data version  
            for f in *; do
                ext="${f#*.}"
                filename="{f%%.*}"
                (mv $f "trial-hg38-gaps-v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_trial-hg38-gaps-v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_trial-hg38-gaps-v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_trial-hg38-gaps-v1_dir"
            recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g')"

            activate_dir="$env_dir/etc/conda/activate.d"
            deactivate_dir="$env_dir/etc/conda/deactivate.d"

            mkdir -p $activate_dir
            mkdir -p $deactivate_dir

            echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
            echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

            #### File
            if [[ ! -z "${recipe_env_file_name:-}" ]] ## If the file env variable exists, set the env file var
            then
                echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
                echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
            fi

            echo 'Recipe successfully built!'
    """, from_string=True)

    recipe.write_recipes()

    ## Test a normal run of _build()
    recipe_dir_path = recipe.recipe_dirs["trial-hg38-gaps-v1"] 
    ## Set global recipe path
    pytest.global_ggd_recipe_path = recipe_dir_path
    ## Get yaml file
    yaml_file = yaml.load(open(os.path.join(recipe_dir_path, "meta.yaml")))
    tarball_file_path = check_recipe._build(recipe_dir_path,yaml_file)
    ## Set global taraball file path
    pytest.global_tarball_testing_file = tarball_file_path
    assert os.path.isfile(tarball_file_path)
    assert "noarch" in tarball_file_path


def test__install_bad_run():
    """
    Test the _install method to properly handels a bad install 
    """

    bz2_file = pytest.global_tarball_testing_file
    recipe_name = "bad-recipe"

    ## If fails, the tarball was not created 
    assert os.path.exists(pytest.global_tarball_testing_file)

    ## Test a bad recipe run
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe._install(bz2_file,recipe_name)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1


def test__install_bad_recipe():
    """
    Test that _install function properly handles a bad recipe
    """

    ## testing-hg38-gaps-v1 recipe as of 3/27/2019 (recipe modified)
    recipe = CreateRecipe(
    """
    bad-recipe-hg38-gaps-v1:
        meta.yaml: |
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              noarch: generic
              number: 0
            extra:
              authors: mjc 
              extra-files: []
            package:
              name: bad-recipe-hg38-gaps-v1
              version: '1' 
            requirements:
              build:
              - gsort
              - htslib
              - zlib
              run:
              - gsort
              - htslib
              - zlib
            source:
              path: .
            about:
              identifiers:
                genome-build: hg38
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: hg38 Assembly gaps from USCS
              tags:
                data-version: 11-Mar-2019
                ggd-channel: genomics
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg38/hg38.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg38/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > gaps.bed.gz
            |
            |
            bad recipe
            gerp grep gper grpe 
            mv > to > something

            tabix gaps.bed.gz 
        
        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/bad-recipe-hg38-gaps-v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/bad-recipe-hg38-gaps-v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg38/bad-recipe-hg38-gaps-v1/1
            fi

            PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

            if [ -d $RECIPE_DIR ]; then
                rm -r $RECIPE_DIR
            fi

            mkdir -p $RECIPE_DIR

            (cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

            cd $RECIPE_DIR

            ## Iterate over new files and replace file name with data package name and data version  
            for f in *; do
                ext="${f#*.}"
                filename="{f%%.*}"
                (mv $f "bad-recipe-hg38-gaps-v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_bad-recipe-hg38-gaps-v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_bad-recipe-hg38-gaps-v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_bad-recipe-hg38-gaps-v1_dir"
            recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g')"

            activate_dir="$env_dir/etc/conda/activate.d"
            deactivate_dir="$env_dir/etc/conda/deactivate.d"

            mkdir -p $activate_dir
            mkdir -p $deactivate_dir

            echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
            echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

            #### File
            if [[ ! -z "${recipe_env_file_name:-}" ]] ## If the file env variable exists, set the env file var
            then
                echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
                echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
            fi


            echo 'Recipe successfully built!'
    """, from_string=True)

    recipe.write_recipes()

    ## Build the recipe using the _build function
    recipe_dir_path = recipe.recipe_dirs["bad-recipe-hg38-gaps-v1"] 
    yaml_file = yaml.load(open(os.path.join(recipe_dir_path, "meta.yaml")))
    tarball_file_path = check_recipe._build(recipe_dir_path,yaml_file)
    recipe_name = "bad-recipe-hg38-gaps-v1"

    ## Test the _install function prorperly uninstalls testing-hg38-gaps-v1 becuse of a bad recipe
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe._install(tarball_file_path,recipe_name)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1

    out = utils.check_output(["conda", "list", "bad-recipe-hg38-gaps-v1"])
    assert "bad-recipe-hg38-gaps-v1" not in out
    out = utils.check_output(["ggd", "show-env"])
    assert "ggd_bad_recipe_hg38_gaps_v1" not in out
    conda_root = utils.conda_root()
    assert os.path.exists(os.path.join(conda_root,"share/ggd/Homo_sapiens/hg38/bad-recipe-hg38-gaps-v1/1")) == False 
    

def test__install_normal_run():
    """
    Test the _install method to properly install the trial-hg38-gaps-v1 package build using the "testing__build_normal_run" test
    """
    ## Remove fragment files
    jdict = ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'trial-hg38-gaps-v1': 
                        {u'activate.d': False, u'version': u'1', u'tags': {u'ggd-channel': u'genomics', 
                        u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, 
                        u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/trial-hg38-gaps-v1-1-0.tar.bz2', 
                        u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'hg38 Assembly gaps from USCS', 
                        u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    uninstall.check_for_installation("trial-hg38-gaps-v1", jdict)

    ## Rerun the _build 
    test__build_normal_run()

    ## get bz2 file
    bz2_file = pytest.global_tarball_testing_file
    ## If fails, the tarball was not created 
    assert os.path.exists(pytest.global_tarball_testing_file)

    recipe_name = "trial-hg38-gaps-v1"
    assert check_recipe._install(bz2_file, recipe_name) == True
   

def test_get_recipe_from_bz2():
    """
    Test that get_recipe_from_bz2 function. 
    """
    
    ## Use the previously created tarball.bz2 file from runing the _build funtion
    bz2_file = pytest.global_tarball_testing_file
    assert os.path.exists(pytest.global_tarball_testing_file)

    metafile = check_recipe.get_recipe_from_bz2(bz2_file)
    assert metafile["build"]["noarch"] == "generic"
    assert metafile["build"]["number"] == "0"
    assert metafile["extra"]["authors"] == "mjc"
    assert metafile["package"]["name"] == "trial-hg38-gaps-v1"
    assert metafile["package"]["version"] == "1"
    assert "gsort" in ",".join(metafile["requirements"]["build"]) 
    assert "htslib" in ",".join(metafile["requirements"]["build"]) 
    assert "zlib" in ",".join(metafile["requirements"]["build"]) 
    assert "gsort" in ",".join(metafile["requirements"]["run"]) 
    assert "htslib" in ",".join(metafile["requirements"]["run"]) 
    assert "zlib" in ",".join(metafile["requirements"]["run"]) 
    assert len(metafile["requirements"]["run"]) == 3
    assert metafile["about"]["identifiers"]["genome-build"] == "hg38"
    assert metafile["about"]["identifiers"]["species"] == "Homo_sapiens"
    assert metafile["about"]["keywords"] == ["gaps","region"]
    assert metafile["about"]["summary"] == "hg38 Assembly gaps from USCS" 
    assert metafile["about"]["tags"]["data-version"] == "11-Mar-2019" 
    assert metafile["about"]["tags"]["ggd-channel"] == "genomics" 


def test__check_build():
    """
    Test the _check_build function to properly handle different genome builds
    """
    
    ## Test Homo_sapiens
    species1 = "Homo_sapiens" 
    build1 = "hg19"
    build2 = "hg38"
    build3 = "GRCh37"
    build4 = "GRCh38"

    assert check_recipe._check_build(species1, build1) == True
    assert check_recipe._check_build(species1, build2) == True
    assert check_recipe._check_build(species1, build3) == True
    assert check_recipe._check_build(species1, build4) == True

    ## Test Mus_musculus
    species2 = "Mus_musculus" 
    build5 = "mm10"
    build6 = "mm9"

    assert check_recipe._check_build(species2, build5) == True
    assert check_recipe._check_build(species2, build6) == True

    ## Test Drosophila_melanogaster
    species3 = "Drosophila_melanogaster" 
    build7 = "dm3"
    build8 = "dm6"

    assert check_recipe._check_build(species3, build7) == True
    assert check_recipe._check_build(species3, build8) == True

    ## Test Canis_familiaris
    species4 = "Canis_familiaris" 
    build9 = "canFam3"

    assert check_recipe._check_build(species4, build9) == True

    ## Test bad species
    species5 = "bad-species" 
    build10 = "hg19"

    try:
        temp_stderr = StringIO()
        with redirect_stderr(temp_stderr):
            check_recipe._check_build(species5, build10)
    except Exception as e:
        output = temp_stderr.getvalue().strip() 
        assert "ERROR: genome-build: hg19 not found in github repo for the bad-species species" in str(output)

    ## Test bad build
    species6 = "Homo_sapiens" 
    build11 = "bad-build"

    try:
        temp_stderr = StringIO()
        with redirect_stderr(temp_stderr):
            check_recipe._check_build(species6, build11)
    except Exception as e:
        output = temp_stderr.getvalue().strip() 
        assert "ERROR: genome-build: bad-build not found in github repo for the Homo_sapiens species" in str(output)


def test_check_recipe_bz2_file():
    """
    Test the main check_recipe funtion using an already build recipe ready for installation
    """
    ## Uninstall the already installed recipe
    try:
        sp.check_call(["conda", "uninstall", "trial-hg38-gaps-v1"])
    except Exception as e:
        pass

    ## Remove fragment files
    jdict = ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'trial-hg38-gaps-v1': 
                        {u'activate.d': False, u'version': u'1', u'tags': {u'ggd-channel': u'genomics', 
                        u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, 
                        u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/trial-hg38-gaps-v1-1-0.tar.bz2', 
                        u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'hg38 Assembly gaps from USCS', 
                        u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    uninstall.check_for_installation("trial-hg38-gaps-v1", jdict)

    ## Buid the bz2 file
    test__build_normal_run()

    ## Use the previously created tarball.bz2 file from runing the _build funtion
    bz2_file = pytest.global_tarball_testing_file
    assert os.path.exists(bz2_file)
    assert os.path.isfile(bz2_file)

    ## Set args
    args = Namespace(command='check-recipe', debug=False, recipe_path=bz2_file)

    check_recipe.check_recipe((),args) == True
   
    out = utils.check_output(["conda", "list", "trial-hg38-gaps-v1"])
    assert "trial-hg38-gaps-v1" in out
    out = utils.check_output(["ggd", "show-env"])
    assert "ggd_trial_hg38_gaps_v1" in out
    conda_root = utils.conda_root()
    assert os.path.exists(os.path.join(conda_root,"share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1")) == True 

    
def test_check_recipe_recipe_path():
    """
    Test the main check_recipe funtion using an recipe path to install a ggd recipe
    """
    ## Uninstall the already installed recipe
    try:
        sp.check_call(["conda", "uninstall", "trial-hg38-gaps-v1"])
    except Exception as e:
        pass

    ## Remove fragment files
    jdict = ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'trial-hg38-gaps-v1': 
                        {u'activate.d': False, u'version': u'1', u'tags': {u'ggd-channel': u'genomics', 
                        u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, 
                        u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/trial-hg38-gaps-v1-1-0.tar.bz2', 
                        u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'hg38 Assembly gaps from USCS', 
                        u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}


    uninstall.check_for_installation("trial-hg38-gaps-v1", jdict)


    ## Uces the previously created ggd recipe path
    recipe_path = pytest.global_ggd_recipe_path
    assert os.path.exists(recipe_path)

    ## Set args
    args = Namespace(command='check-recipe', debug=False, recipe_path=recipe_path)
   
    assert check_recipe.check_recipe((),args) == True
    out = utils.check_output(["conda", "list", "trial-hg38-gaps-v1"])
    assert "trial-hg38-gaps-v1" in out
    out = utils.check_output(["ggd", "show-env"])
    assert "ggd_trial_hg38_gaps_v1" in out
    conda_root = utils.conda_root()
    assert os.path.exists(os.path.join(conda_root,"share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-v1/1")) == True 


def test_check_recipe_package_env_vars():
    """
    Use the check_recipe main function to test that the correct environment variables are created. 
        1) If one file, a env_var for the file and the dir are created
        2) If two files and one of them is an index, an env_var for the non-indexed file and the dir
        3) If two files without an index, an env_var for only the dir
        4) If three+ files, an env_var for only the dir
    """

    ## Test that an env_var is created for a single installed file and the dir
    recipe = CreateRecipe(
    """
    one_file_v1:
        meta.yaml: |
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              noarch: generic
              number: 0
            extra:
              authors: mjc 
              extra-files: 
              - one_file_v1.bw
            package:
              name: one_file_v1
              version: '1' 
            requirements:
              build:
              - gsort
              - htslib
              - zlib
              run:
              - gsort
              - htslib
              - zlib
            source:
              path: .
            about:
              identifiers:
                genome-build: hg19
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: testing env_var for recipe with one file
              tags:
                data-version: Today
                ggd-channel: genomics
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset
            wget --quiet --no-check-certificate --output-document hg19phastcons.bw http://hgdownload.cse.ucsc.edu/goldenpath/hg19/phastCons100way/hg19.100way.phastCons.bw

        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg19/one_file_v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg19/one_file_v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg19/one_file_v1/1
            fi

            PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

            if [ -d $RECIPE_DIR ]; then
                rm -r $RECIPE_DIR
            fi

            mkdir -p $RECIPE_DIR

            (cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

            cd $RECIPE_DIR

            ## Iterate over new files and replace file name with data package name and data version  
            for f in *; do
                ext="${f#*.}"
                filename="{f%%.*}"
                (mv $f "one_file_v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_one_file_v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_one_file_v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_one_file_v1_dir"
            recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g')"

            activate_dir="$env_dir/etc/conda/activate.d"
            deactivate_dir="$env_dir/etc/conda/deactivate.d"

            mkdir -p $activate_dir
            mkdir -p $deactivate_dir

            echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
            echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

            #### File
            if [[ ! -z "${recipe_env_file_name:-}" ]] ## If the file env variable exists, set the env file var
            then
                echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
                echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
            fi

            echo 'Recipe successfully built!'
    """, from_string=True)

    recipe.write_recipes()
    recipe_dir_path = recipe.recipe_dirs["one_file_v1"] 
    args = Namespace(command='check-recipe', debug=False, recipe_path=recipe_dir_path)
    assert check_recipe.check_recipe((),args) == True
    ## Test dir and file env_var
    conda_root = utils.conda_root()
    with open(os.path.join(conda_root,"etc/conda/activate.d/env_vars.sh")) as env_file:
        env_vars = [x for x in env_file if "ggd_one_file_v1_dir" in x or "ggd_one_file_v1_file" in x]
        first = False
        second = False
        for x in env_vars:
            if "ggd_one_file_v1_dir" in x:
                assert os.path.join(conda_root, "share/ggd/Homo_sapiens/hg19/one_file_v1/1") in x
                first = True
            elif "ggd_one_file_v1_file" in x:
                assert os.path.join(conda_root, "share/ggd/Homo_sapiens/hg19/one_file_v1/1/one_file_v1.bw")
                second = True
            else:
                assert False
        assert first == True
        assert second == True


    args = Namespace(command="show-env", pattern=None)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.show_env((),args)
    output = temp_stdout.getvalue().strip()
    assert "$ggd_one_file_v1_file" in output
    assert "$ggd_one_file_v1_dir" in output

    ## Test that an env_var is created for the non indexed file when two files are installed with an index present, and the dir
    recipe = CreateRecipe(
    """
    two_files_v1:
        meta.yaml: |
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              noarch: generic
              number: 0
            extra:
              authors: mjc 
              extra-files: []
            package:
              name: two_files_v1
              version: '1' 
            requirements:
              build:
              - gsort
              - htslib
              - zlib
              run:
              - gsort
              - htslib
              - zlib
            source:
              path: .
            about:
              identifiers:
                genome-build: hg19
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: testing env_var for recipe with two files and an index present
              tags:
                data-version: Today
                ggd-channel: genomics
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset
            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg19/hg19.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg19/database/gap.txt.gz \
                | gzip -dc \
                | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \
                | gsort /dev/stdin $genome \
                | bgzip -c > gaps.bed.gz

            tabix gaps.bed.gz

        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg19/two_files_v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg19/two_files_v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg19/two_files_v1/1
            fi

            PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

            if [ -d $RECIPE_DIR ]; then
                rm -r $RECIPE_DIR
            fi

            mkdir -p $RECIPE_DIR

            (cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

            cd $RECIPE_DIR

            ## Iterate over new files and replace file name with data package name and data version  
            for f in *; do
                ext="${f#*.}"
                filename="{f%%.*}"
                (mv $f "two_files_v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_two_files_v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_two_files_v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_two_files_v1_dir"
            recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g')"

            activate_dir="$env_dir/etc/conda/activate.d"
            deactivate_dir="$env_dir/etc/conda/deactivate.d"

            mkdir -p $activate_dir
            mkdir -p $deactivate_dir

            echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
            echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

            #### File
            if [[ ! -z "${recipe_env_file_name:-}" ]] ## If the file env variable exists, set the env file var
            then
                echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
                echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
            fi

            echo 'Recipe successfully built!'
    """, from_string=True)

    recipe.write_recipes()
    recipe_dir_path = recipe.recipe_dirs["two_files_v1"] 
    args = Namespace(command='check-recipe', debug=False, recipe_path=recipe_dir_path)
    assert check_recipe.check_recipe((),args) == True
    ## Test dir and file env_var
    conda_root = utils.conda_root()
    with open(os.path.join(conda_root,"etc/conda/activate.d/env_vars.sh")) as env_file:
        env_vars = [x for x in env_file if "ggd_two_files_v1_dir" in x or "ggd_two_files_v1_file" in x]
        first = False
        second = False
        for x in env_vars:
            if "ggd_two_files_v1_dir" in x:
                assert os.path.join(conda_root, "share/ggd/Homo_sapiens/hg19/two_files_v1/1") in x
                first = True
            elif "ggd_two_files_v1_file" in x:
                assert os.path.join(conda_root, "share/ggd/Homo_sapiens/hg19/two_files_v1/1/two_files_v1.bed.gz")
                second = True
            else:
                assert False
        assert first == True
        assert second == True

    args = Namespace(command="show-env", pattern=None)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.show_env((),args)
    output = temp_stdout.getvalue().strip()
    assert "$ggd_two_files_v1_file" in output
    assert "$ggd_two_files_v1_dir" in output   

    ## Test that NO env_var is created when two files are installed with no index present, and the dir
    recipe = CreateRecipe(
    """
    two_files_noindex_v1:
        meta.yaml: |
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              noarch: generic
              number: 0
            extra:
              authors: mjc 
              extra-files: 
              - two_files_noindex_v1.genome
              - two_files_noindex_v1.txt.gz
            package:
              name: two_files_noindex_v1
              version: '1' 
            requirements:
              build:
              - gsort
              - htslib
              - zlib
              run:
              - gsort
              - htslib
              - zlib
            source:
              path: .
            about:
              identifiers:
                genome-build: hg19
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: testing NO file env_var for recipe with two files and no index
              tags:
                data-version: Today
                ggd-channel: genomics
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset
            wget --quiet https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg19/hg19.genome
            wget --quiet http://hgdownload.cse.ucsc.edu/goldenpath/hg19/database/gap.txt.gz 

        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg19/two_files_noindex_v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg19/two_files_noindex_v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg19/two_files_noindex_v1/1
            fi

            PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

            if [ -d $RECIPE_DIR ]; then
                rm -r $RECIPE_DIR
            fi

            mkdir -p $RECIPE_DIR

            (cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

            cd $RECIPE_DIR

            ## Iterate over new files and replace file name with data package name and data version  
            for f in *; do
                ext="${f#*.}"
                filename="{f%%.*}"
                (mv $f "two_files_noindex_v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_two_files_noindex_v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_two_files_noindex_v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_two_files_noindex_v1_dir"
            recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g')"

            activate_dir="$env_dir/etc/conda/activate.d"
            deactivate_dir="$env_dir/etc/conda/deactivate.d"

            mkdir -p $activate_dir
            mkdir -p $deactivate_dir

            echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
            echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

            #### File
            if [[ ! -z "${recipe_env_file_name:-}" ]] ## If the file env variable exists, set the env file var
            then
                echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
                echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
            fi

            echo 'Recipe successfully built!'
    """, from_string=True)

    recipe.write_recipes()
    recipe_dir_path = recipe.recipe_dirs["two_files_noindex_v1"] 
    args = Namespace(command='check-recipe', debug=False, recipe_path=recipe_dir_path)
    assert check_recipe.check_recipe((),args) == True
    ## Test dir and file env_var
    conda_root = utils.conda_root()
    with open(os.path.join(conda_root,"etc/conda/activate.d/env_vars.sh")) as env_file:
        env_vars = [x for x in env_file if "ggd_two_files_noindex_v1_dir" in x or "ggd_two_files_noindex_v1_file" in x]
        first = False
        for x in env_vars:
            if "ggd_two_files_noindex_v1_dir" in x:
                assert os.path.join(conda_root, "share/ggd/Homo_sapiens/hg19/two_files_noindex_v1/1") in x
                first = True
            elif "ggd_two_files_noindex_v1_file" in x:
                assert False ## There should not be a file env_var made for this package
            else:
                assert False
        assert first == True

    args = Namespace(command="show-env", pattern=None)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.show_env((),args)
    output = temp_stdout.getvalue().strip()
    assert "$ggd_two_files_noindex_v1_file" not in output
    assert "$ggd_two_files_noindex_v1_dir" in output

    ## Test that NO env_var is created when thre+ files are installed, and the dir
    recipe = CreateRecipe(
    """
    three_files_v1:
        meta.yaml: |
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              noarch: generic
              number: 0
            extra:
              authors: mjc 
              extra-files: 
              - three_files_v1.genome
              - three_files_v1.1.txt.gz
              - three_files_v1.2.txt.gz
            package:
              name: three_files_v1
              version: '1' 
            requirements:
              build:
              - gsort
              - htslib
              - zlib
              run:
              - gsort
              - htslib
              - zlib
            source:
              path: .
            about:
              identifiers:
                genome-build: hg19
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: testing NO file env_var for recipe with three+ files
              tags:
                data-version: Today
                ggd-channel: genomics
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset
            wget --quiet https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg19/hg19.genome
            wget --quiet http://hgdownload.cse.ucsc.edu/goldenpath/hg19/database/gap.txt.gz 
            cp gap.txt.gz gaps.1.txt.gz
            mv gap.txt.gz gaps.2.txt.gz

        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg19/three_files_v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg19/three_files_v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg19/three_files_v1/1
            fi

            PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

            if [ -d $RECIPE_DIR ]; then
                rm -r $RECIPE_DIR
            fi

            mkdir -p $RECIPE_DIR

            (cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)

            cd $RECIPE_DIR

            ## Iterate over new files and replace file name with data package name and data version  
            for f in *; do
                ext="${f#*.}"
                filename="{f%%.*}"
                (mv $f "three_files_v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_three_files_v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_three_files_v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_three_files_v1_dir"
            recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g')"

            activate_dir="$env_dir/etc/conda/activate.d"
            deactivate_dir="$env_dir/etc/conda/deactivate.d"

            mkdir -p $activate_dir
            mkdir -p $deactivate_dir

            echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh
            echo "unset $recipe_env_dir_name">> $deactivate_dir/env_vars.sh

            #### File
            if [[ ! -z "${recipe_env_file_name:-}" ]] ## If the file env variable exists, set the env file var
            then
                echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh
                echo "unset $recipe_env_file_name">> $deactivate_dir/env_vars.sh
            fi

            echo 'Recipe successfully built!'
    """, from_string=True)

    recipe.write_recipes()
    recipe_dir_path = recipe.recipe_dirs["three_files_v1"] 
    args = Namespace(command='check-recipe', debug=False, recipe_path=recipe_dir_path)
    assert check_recipe.check_recipe((),args) == True
    ## Test dir and file env_var
    conda_root = utils.conda_root()
    with open(os.path.join(conda_root,"etc/conda/activate.d/env_vars.sh")) as env_file:
        env_vars = [x for x in env_file if "ggd_three_files_v1_dir" in x or "ggd_three_files_v1_file" in x]
        first = False
        for x in env_vars:
            if "ggd_three_files_v1_dir" in x:
                assert os.path.join(conda_root, "share/ggd/Homo_sapiens/hg19/three_files_v1/1") in x
                first = True
            elif "ggd_three_files_v1_file" in x:
                assert False ## There should not be a file env_var made for this package
            else:
                assert False
        assert first == True

    args = Namespace(command="show-env", pattern=None)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.show_env((),args)
    output = temp_stdout.getvalue().strip()
    assert "$ggd_three_files_v1_file" not in output
    assert "$ggd_three_files_v1_dir" in output


def test_get_modified_files():
    """
    Test the get_modified_files correctly returns the modified files 
    """

    ## Create temporary files
    files = CreateRecipe(
    """
    files:
        file0: |
            This is file0
        file1: |
            This is file1
        file2: |
            This is file2
        file3: |
            This is file3
        file4: |
            This is file4
        file5: |
            This is file5
        file6:
            This is file6
        file7:
            This is file7
    """, from_string=True)

    files.write_recipes()
    files_path = files.recipe_dirs["files"]

    inital_files_tuples = check_recipe.list_files(files_path)

    ## Modify even numbered files
    time.sleep(1)
    for i, file_tuple in enumerate(inital_files_tuples):
        if i % 2 == 0:
            print("Modifying: %s" %file_tuple[0])
            with open(file_tuple[0], "a") as f:
                f.write("Modified")

    ## Get modified files
    modified_files_tuples = check_recipe.list_files(files_path) 
    filtered_list = check_recipe.get_modified_files(modified_files_tuples, inital_files_tuples)

    ## check modified and un-modified files
    for i, file_tuple in enumerate(inital_files_tuples):
        if i % 2 == 0:
            assert file_tuple[0] in filtered_list
        else:
            assert file_tuple[0] not in filtered_list



def test_check_files_good_genomic_file():
    """
    Test the check_files function to properly check genomic file pairs
    """

    files = CreateRecipe(
    """
    genomicfiles:
        test.fa: |
            >chr1
            CTGAAGAACTGTCTGCACCCAGGGCAGAGATTACGGGGTTCTGAGGTTCCCCCGCCCCGCGGCCTCTCTT
            GGCGGCTGTGCGTGTTCAGTTGCCTTCATTGAAACCCAAGCATCCGTCCTCGGCTGCCACCGACACAGGT
            CAAGGCCACCCAGGAGGAGACACTGTGGGGCCCTGCCCAGTTCTCACGGGTATCGCATTTTGGCAGGACG
            >chr2
            GGCGGCTGTGCGTGTTCAGTTGCCTTCATTGAAACCCAAGCATCCGTCCTCGGCTGCCACCGACACAGGT
            CAAGGCCACCCAGGAGGAGACACTGTGGGGCCCTGCCCAGTTCTCACGGGTATCGCATTTTGGCAGGACG
            CTGAAGAACTGTCTGCACCCAGGGCAGAGATTACGGGGTTCTGAGGTTCCCCCGCCCCGCGGCCTCTCTT
            >chr3
            CAAGGCCACCCAGGAGGAGACACTGTGGGGCCCTGCCCAGTTCTCACGGGTATCGCATTTTGGCAGGACG
            CTGAAGAACTGTCTGCACCCAGGGCAGAGATTACGGGGTTCTGAGGTTCCCCCGCCCCGCGGCCTCTCTT
            GGCGGCTGTGCGTGTTCAGTTGCCTTCATTGAAACCCAAGCATCCGTCCTCGGCTGCCACCGACACAGGT
        test.fa.fai: |
            chr1\t249250621\t6\t50\t51  
            chr2\t243199373\t254235646\t50\t51  
            chr3\t198022430\t502299013\t50\t51  
            chr4\t191154276\t704281898\t50\t51  
            chr5\t180915260\t899259266\t50\t51  
        cpg.bed: |
            chr1\t28735\t29810\tCpG: 116
            chr1\t135124\t135563\tCpG: 30
            chr1\t327790\t328229\tCpG: 29
            chr1\t437151\t438164\tCpG: 84
            chr1\t449273\t450544\tCpG: 99
            chr1\t533219\t534114\tCpG: 94
            chr1\t544738\t546649\tCpG: 171
            chr1\t713984\t714547\tCpG: 60
            chr1\t762416\t763445\tCpG: 115
            chr1\t788863\t789211\tCpG: 28
        some.vcf: |
            ##fileformat=VCFv4.2
            ##ALT=<ID=NON_REF,Description="Represents any possible alternative allele at this location">
            ##FILTER=<ID=LowQual,Description="Low quality">
            ##FORMAT=<ID=RGQ,Number=1,Type=Integer,Description="Unconditional reference genotype confidence, encoded as a phred quality -10*log10 p(
            ##INFO=<ID=set,Number=1,Type=String,Description="Source VCF for the merged record in CombineVariants">
            ##reference=file:///scratch/ucgd/lustre/ugpuser/ucgd_data/references/human_g1k_v37_decoy.fasta
            #CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO    
            chr1\t69270\t.\tA\tG\t206020.99\tPASS\tAC=959;AF=0.814;AN=1178;BaseQRankSum=1.20;ClippingRankSum=0.433;DP=15730;ExcessHet=0.0000;FS
            chr1\t69428\t.\tT\tG\t13206.32 \tPASS\tAC=37;AF=0.028;AN=1302;BaseQRankSum=0.727;ClippingRankSum=0.842;DP=25114;ExcessHet=-0.0000;F
            chr1\t69511\t.\tA\tG\t843359.35\tPASS\tAC=1094;AF=0.943;AN=1160;BaseQRankSum=0.736;ClippingRankSum=-3.200e-02;DP=55870;ExcessHet=-0
            chr1\t69552\t.\tG\tC\t616.05\tPASS\tAC=2;AF=1.701e-03;AN=1176;BaseQRankSum=2.06;ClippingRankSum=1.25;DP=28398;ExcessHet=3.0214;FS=8.
            chr1\t69761\t.\tA\tT\t47352.67\t.\tAC=147;AF=0.096;AN=1524;BaseQRankSum=0.713;ClippingRankSum=0.056;DP=10061;ExcessHet=-0.0000;FS=5
        hg19.gtf: |
            chr1\thg19_knownGene\texon\t11874\t12227\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
            chr1\thg19_knownGene\tstart_codon\t12190\t12192\t0.000000\t+\t.\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\tCDS\t12190\t12227\t0.000000\t+\t0\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\texon\t12595\t12721\t0.000000\t+\t.\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\texon\t12613\t12721\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
            chr1\thg19_knownGene\texon\t13221\t14409\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
        hg19.gff: |
            chr1\thg19_knownGene\texon\t11874\t12227\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
            chr1\thg19_knownGene\tstart_codon\t12190\t12192\t0.000000\t+\t.\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\tCDS\t12190\t12227\t0.000000\t+\t0\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\texon\t12595\t12721\t0.000000\t+\t.\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\texon\t12613\t12721\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
            chr1\thg19_knownGene\texon\t13221\t14409\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
        hg19.gff3: |
            ##gff-version   3
            ##sequence-region   1 1 249250621
            ##sequence-region   10 1 135534747
            ##sequence-region   11 1 135006516
            ##sequence-region   12 1 133851895
            ##sequence-region   13 1 115169878
            chr1\tEponine\tbiological_region\t10650\t10657\t0.999\t+\t.\tlogic_name=eponine
            chr1\tEponine\tbiological_region\t10656\t10658\t0.999\t-\t.\tlogic_name=eponine
            chr1\tEponine\tbiological_region\t10678\t10687\t0.999\t+\t.\tlogic_name=eponine
            chr1\tEponine\tbiological_region\t10682\t10689\t0.999\t-\t.\tlogic_name=eponine
    """, from_string=True)
    
    files.write_recipes()

    files_path = files.recipe_dirs["genomicfiles"]   

    ## Create a .gz and .gz.tbi file for each genomic file other than .fa
    for f in os.listdir(files_path):
        if ".fa" not in f:
            sp.check_output("bgzip -c "+os.path.join(files_path,f)+" > "+os.path.join(files_path,f)+".gz", shell=True)
            out = sp.check_output("tabix "+os.path.join(files_path,f)+".gz", shell=True)

    species = "Homo_sapiens"
    build = "hg19"
    name = "testing-hg19-recipe-v1"
    file_tuples = check_recipe.list_files(files_path)

    ## Test that unmodified files causes the system to exit(2)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe.check_files(files_path, species, build, name, [],file_tuples)  
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## Check that the exit code is 1

    ## Modify files
    time.sleep(1)
    for file_tuple in file_tuples:
        sp.check_output(["touch", "-m", file_tuple[0]])

    ## Check correct run of check_files
    assert check_recipe.check_files(files_path, species, build, name, [],file_tuples) == True  


def test_check_files_unpaired_genomic_file():
    """
    Test the check_files function to properly check genomic file pairs and fail if the pairs are incorrectly present
    """

    species = "Homo_sapiens"
    build = "hg19"
    name = "testing-hg19-recipe-v1"

    ## Test each file type for checking... fasta, bed, vcf, gff, gtf, etc.
    fastafile = CreateRecipe(
    """
    fastafile:
        test.fa: |
            >chr1
            CTGAAGAACTGTCTGCACCCAGGGCAGAGATTACGGGGTTCTGAGGTTCCCCCGCCCCGCGGCCTCTCTT
            GGCGGCTGTGCGTGTTCAGTTGCCTTCATTGAAACCCAAGCATCCGTCCTCGGCTGCCACCGACACAGGT
            CAAGGCCACCCAGGAGGAGACACTGTGGGGCCCTGCCCAGTTCTCACGGGTATCGCATTTTGGCAGGACG
            >chr2
            GGCGGCTGTGCGTGTTCAGTTGCCTTCATTGAAACCCAAGCATCCGTCCTCGGCTGCCACCGACACAGGT
            CAAGGCCACCCAGGAGGAGACACTGTGGGGCCCTGCCCAGTTCTCACGGGTATCGCATTTTGGCAGGACG
            CTGAAGAACTGTCTGCACCCAGGGCAGAGATTACGGGGTTCTGAGGTTCCCCCGCCCCGCGGCCTCTCTT
            >chr3
            CAAGGCCACCCAGGAGGAGACACTGTGGGGCCCTGCCCAGTTCTCACGGGTATCGCATTTTGGCAGGACG
            CTGAAGAACTGTCTGCACCCAGGGCAGAGATTACGGGGTTCTGAGGTTCCCCCGCCCCGCGGCCTCTCTT
            GGCGGCTGTGCGTGTTCAGTTGCCTTCATTGAAACCCAAGCATCCGTCCTCGGCTGCCACCGACACAGGT
    """, from_string=True)
    
    fastafile.write_recipes()
    files_path = fastafile.recipe_dirs["fastafile"]   

    file_tuples = check_recipe.list_files(files_path)
    ## Modify the files
    for file_tuple in file_tuples:
        sp.check_output(["touch", "-m", file_tuple[0]])

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe.check_files(files_path, species, build, name, [],file_tuples)  
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## Check that the exit code is 1

    bedfiles = CreateRecipe(
    """
    bedfiles:
        cpg.bed: |
            chr1\t28735\t29810\tCpG: 116
            chr1\t135124\t135563\tCpG: 30
            chr1\t327790\t328229\tCpG: 29
            chr1\t437151\t438164\tCpG: 84
            chr1\t449273\t450544\tCpG: 99
            chr1\t533219\t534114\tCpG: 94
            chr1\t544738\t546649\tCpG: 171
            chr1\t713984\t714547\tCpG: 60
            chr1\t762416\t763445\tCpG: 115
            chr1\t788863\t789211\tCpG: 28
    """, from_string=True)
    
    bedfiles.write_recipes()
    files_path = bedfiles.recipe_dirs["bedfiles"]   
    for f in os.listdir(files_path):
        sp.check_output("bgzip -c "+os.path.join(files_path,f)+" > "+os.path.join(files_path,f)+".gz", shell=True)

    file_tuples = check_recipe.list_files(files_path)
    ## Modify the files
    for file_tuple in file_tuples:
        sp.check_output(["touch", "-m", file_tuple[0]])
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe.check_files(files_path, species, build, name, [],file_tuples)  
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## Check that the exit code is 1

    vcffiles = CreateRecipe(
    """
    vcffiles:
        some.vcf: |
            ##fileformat=VCFv4.2
            ##ALT=<ID=NON_REF,Description="Represents any possible alternative allele at this location">
            ##FILTER=<ID=LowQual,Description="Low quality">
            ##FORMAT=<ID=RGQ,Number=1,Type=Integer,Description="Unconditional reference genotype confidence, encoded as a phred quality -10*log10 p(
            ##INFO=<ID=set,Number=1,Type=String,Description="Source VCF for the merged record in CombineVariants">
            ##reference=file:///scratch/ucgd/lustre/ugpuser/ucgd_data/references/human_g1k_v37_decoy.fasta
            #CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO    
            chr1\t69270\t.\tA\tG\t206020.99\tPASS\tAC=959;AF=0.814;AN=1178;BaseQRankSum=1.20;ClippingRankSum=0.433;DP=15730;ExcessHet=0.0000;FS
            chr1\t69428\t.\tT\tG\t13206.32 \tPASS\tAC=37;AF=0.028;AN=1302;BaseQRankSum=0.727;ClippingRankSum=0.842;DP=25114;ExcessHet=-0.0000;F
            chr1\t69511\t.\tA\tG\t843359.35\tPASS\tAC=1094;AF=0.943;AN=1160;BaseQRankSum=0.736;ClippingRankSum=-3.200e-02;DP=55870;ExcessHet=-0
            chr1\t69552\t.\tG\tC\t616.05\tPASS\tAC=2;AF=1.701e-03;AN=1176;BaseQRankSum=2.06;ClippingRankSum=1.25;DP=28398;ExcessHet=3.0214;FS=8.
            chr1\t69761\t.\tA\tT\t47352.67\t.\tAC=147;AF=0.096;AN=1524;BaseQRankSum=0.713;ClippingRankSum=0.056;DP=10061;ExcessHet=-0.0000;FS=5
    """, from_string=True)
    
    vcffiles.write_recipes()
    files_path = vcffiles.recipe_dirs["vcffiles"]   
    for f in os.listdir(files_path):
        sp.check_output("bgzip -c "+os.path.join(files_path,f)+" > "+os.path.join(files_path,f)+".gz", shell=True)

    file_tuples = check_recipe.list_files(files_path)
    ## Modify the files
    for file_tuple in file_tuples:
        sp.check_output(["touch", "-m", file_tuple[0]])

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe.check_files(files_path, species, build, name, [],file_tuples)  
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## Check that the exit code is 1

    gtffiles = CreateRecipe(
    """
    gtffiles:
        hg19.gtf: |
            chr1\thg19_knownGene\texon\t11874\t12227\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
            chr1\thg19_knownGene\tstart_codon\t12190\t12192\t0.000000\t+\t.\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\tCDS\t12190\t12227\t0.000000\t+\t0\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\texon\t12595\t12721\t0.000000\t+\t.\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\texon\t12613\t12721\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
            chr1\thg19_knownGene\texon\t13221\t14409\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
    """, from_string=True)
    
    gtffiles.write_recipes()
    files_path = gtffiles.recipe_dirs["gtffiles"]   
    for f in os.listdir(files_path):
        sp.check_output("bgzip -c "+os.path.join(files_path,f)+" > "+os.path.join(files_path,f)+".gz", shell=True)

    file_tuples = check_recipe.list_files(files_path)
    ## Modify the files
    for file_tuple in file_tuples:
        sp.check_output(["touch", "-m", file_tuple[0]])

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe.check_files(files_path, species, build, name, [],file_tuples)  
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## Check that the exit code is 1

    gfffiles = CreateRecipe(
    """
    gfffiles:
        hg19.gff: |
            chr1\thg19_knownGene\texon\t11874\t12227\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
            chr1\thg19_knownGene\tstart_codon\t12190\t12192\t0.000000\t+\t.\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\tCDS\t12190\t12227\t0.000000\t+\t0\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\texon\t12595\t12721\t0.000000\t+\t.\tgene_id "uc010nxq.1"; transcript_id "uc010nxq.1"; 
            chr1\thg19_knownGene\texon\t12613\t12721\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
            chr1\thg19_knownGene\texon\t13221\t14409\t0.000000\t+\t.\tgene_id "uc001aaa.3"; transcript_id "uc001aaa.3"; 
    """, from_string=True)
    
    gfffiles.write_recipes()
    files_path = gfffiles.recipe_dirs["gfffiles"]   
    for f in os.listdir(files_path):
        sp.check_output("bgzip -c "+os.path.join(files_path,f)+" > "+os.path.join(files_path,f)+".gz", shell=True)

    file_tuples = check_recipe.list_files(files_path)
    ## Modify the files
    for file_tuple in file_tuples:
        sp.check_output(["touch", "-m", file_tuple[0]])

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe.check_files(files_path, species, build, name, [],file_tuples)  
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## Check that the exit code is 1

    gff3files = CreateRecipe(
    """
    gff3files:
        hg19.gff3: |
            ##gff-version   3
            ##sequence-region   1 1 249250621
            ##sequence-region   10 1 135534747
            ##sequence-region   11 1 135006516
            ##sequence-region   12 1 133851895
            ##sequence-region   13 1 115169878
            chr1\tEponine\tbiological_region\t10650\t10657\t0.999\t+\t.\tlogic_name=eponine
            chr1\tEponine\tbiological_region\t10656\t10658\t0.999\t-\t.\tlogic_name=eponine
            chr1\tEponine\tbiological_region\t10678\t10687\t0.999\t+\t.\tlogic_name=eponine
            chr1\tEponine\tbiological_region\t10682\t10689\t0.999\t-\t.\tlogic_name=eponine
    """, from_string=True)
    
    gff3files.write_recipes()
    files_path = gff3files.recipe_dirs["gff3files"]   
    for f in os.listdir(files_path):
        sp.check_output("bgzip -c "+os.path.join(files_path,f)+" > "+os.path.join(files_path,f)+".gz", shell=True)

    file_tuples = check_recipe.list_files(files_path)
    ## Modify the files
    for file_tuple in file_tuples:
        sp.check_output(["touch", "-m", file_tuple[0]])

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        check_recipe.check_files(files_path, species, build, name, [],file_tuples)  
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## Check that the exit code is 1


def test_check_yaml():
    """
    Test the check_yaml function  
    """

    recipe = CreateRecipe(
    """
    testing-recipe:
        meta.yaml: |
            build:
              binary_relocation: false
              detect_binary_files_with_prefix: false
              noarch: generic
              number: 0
            extra:
              authors: mjc 
              extra-files: []
            package:
              name: trial-hg38-gaps-v1
              version: '1' 
            requirements:
              build:
              - gsort
              - htslib
              - zlib
              run:
              - gsort
              - htslib
              - zlib
            source:
              path: .
            about:
              identifiers:
                genome-build: hg38
                species: Homo_sapiens
              keywords:
              - gaps
              - region
              summary: hg38 Assembly gaps from USCS
              tags:
                data-version: 11-Mar-2019
                ggd-channel: genomics
    """, from_string=True)

    recipe.write_recipes()

    recipe_dir_path = recipe.recipe_dirs["testing-recipe"]
    yaml_file = yaml.load(open(os.path.join(recipe_dir_path, "meta.yaml")))

    ## Test a good run of check_yaml
    species, build, version = check_recipe.check_yaml(yaml_file)
    assert species == "Homo_sapiens"
    assert build == "hg38"
    assert version == "1"

    yaml_file_copy = deepcopy(yaml_file)     

    del yaml_file["package"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify 'package:' section with ggd version and package name" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["package"]["version"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify 'package:' section with ggd version and package name" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False
    

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["extra"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify 'extra:' section with author and extra-files" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["about"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify an 'about/summary' section" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["about"]["summary"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify an 'about/summary' section" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False
    

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["about"]["identifiers"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify an 'identifier' section in about" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["about"]["identifiers"]["genome-build"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify 'about:' section with genome-build" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["about"]["identifiers"]["species"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify 'about:' section with species" in str(e): 
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["about"]["tags"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify 'about:' section with tags" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["about"]["tags"]["data-version"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify the specific data version of the data in the 'about:tags' section" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["about"]["tags"]["ggd-channel"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify the specific ggd channel for the recipe in the 'about:tags' section" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False

    yaml_file = deepcopy(yaml_file_copy) 
    del yaml_file["about"]["keywords"]
    try:
        check_recipe.check_yaml(yaml_file)
        assert False
    except AssertionError as e:
        if "must specify 'about:' section with keywords" in str(e):
            pass
        else:
            assert False
    except Exception as e:
        print(str(e))
        assert False



