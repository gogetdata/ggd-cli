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
from argparse import Namespace
from argparse import ArgumentParser
import glob
import contextlib
import tarfile
from helpers import CreateRecipe
from ggd import utils
from ggd import make_bash
import oyaml

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO


#---------------------------------------------------------------------------------------------------------
## Test Label
#---------------------------------------------------------------------------------------------------------

TEST_LABEL = "ggd-make-recipe-test"


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
# Unit test for ggd make-recipe
#-----------------------------------------------------------------------------------------------------------------------

def test_make_bash_test_bad_summary():
    """
    Test the main method of ggd make-recipe
    """

    ## test that make_bash fails when a bad summary is provided
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "Please provide a thorough summary of the data package" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

        
    ## test that make_bash fails when a bad summary is provided
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary=' ')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "Please provide a thorough summary of the data package" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False



def test_make_bash_test_bad_name():
    """
    Test the main method of ggd make-recipe
    """

    ## test that make_bash fails when a bad name is provided
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing name
        assert "The recipe name is required" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

        
    ## test that make_bash fails when a bad name is provided
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name=' ', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing name
        assert "The recipe name is required" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False


def test_make_bash_test_wildcards():
    """
    Test the main method of ggd make-recipe, make sure that a name with a wildcard raises and assertion error
    """

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test.gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\".\" wildcard is not allowed in the recipe name" in str(e)
        assert "hg19-test.gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test?gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"?\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test?gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test*gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"*\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test*gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test[gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"[\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test[gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test]gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"]\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test]gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False


    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test{gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"{\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test{gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False


    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test}gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"}\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test}gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False


    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test!gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"!\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test!gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False


    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test+gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"+\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test+gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test^gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"^\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test^gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test$gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"$\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test$gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test(gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"(\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test(gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test)gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC')
    try:
        assert make_bash.make_bash((),args)  
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\")\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test)gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False




def test_make_bash_test_bad_genome_build():
    """
    Test the main method of ggd make-recipe
    """

    ## test that make_bash fails when a bad genome build is provided
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], extra_file=[], genome_build='hg09', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS')

    try:
        temp_stderr = StringIO()
        with redirect_stderr(temp_stderr):
            make_bash.make_bash((),args)  
    except Exception as e:
        os.rmdir("{}-{}-{}-v{}".format("hg09","test-gaps","ucsc","1"))
        output = str(temp_stderr.getvalue().strip()) 
        assert "ERROR: genome-build: hg09 not found in github repo for the Homo_sapiens species" in output

        
    ## test that make_bash fails when a bad genome build is provided
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], extra_file=[], genome_build='hgmm10', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS')
    try:
        temp_stderr = StringIO()
        with redirect_stderr(temp_stderr):
            make_bash.make_bash((),args)  
    except Exception as e:
        os.rmdir("{}-{}-{}-v{}".format("hgmm10","test-gaps","ucsc","1"))
        output = temp_stderr.getvalue().strip() 
        assert "ERROR: genome-build: hgmm10 not found in github repo for the Homo_sapiens species" in output




def test_make_bash_test_bad_recipe():
    """
    Test the main method of ggd make-recipe
    """

    ## test that make_bash fails when a bad recipe is provided
    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='bad-recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS')

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        make_bash.make_bash((), args)
    os.rmdir("{}-{}-{}-v{}".format("hg19","test-gaps","ucsc","1"))
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1




def test_make_bash():
    """
    Test the main method of ggd make-recipe
    """

    recipe = CreateRecipe(

    """
    hg19-test-gaps-ucsc-v1:
        recipe.sh: |

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg19/hg19.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg19/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > gaps.bed.gz

            tabix gaps.bed.gz 

    """, from_string=True)

    recipe.write_recipes() 

    ggd_package = "hg19-test-gaps-ucsc-v1"

    recipe_file = os.path.join(recipe.recipe_dirs["hg19-test-gaps-ucsc-v1"],"recipe.sh")

    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], extra_file=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script=recipe_file, species='Homo_sapiens', summary='Assembly gaps from UCSC')

    assert make_bash.make_bash((),args) 

    new_recipe_file = os.path.join("./", ggd_package, "recipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_metayaml_file = os.path.join("./", ggd_package, "meta.yaml") 
    assert os.path.exists(new_metayaml_file)
    assert os.path.isfile(new_metayaml_file)
    new_postlink_file = os.path.join("./", ggd_package, "post-link.sh") 
    assert os.path.exists(new_postlink_file)
    assert os.path.isfile(new_postlink_file)

    ## Test meta.yaml
    try:
        with open(new_metayaml_file, "r") as mf:
            yamldict = yaml.safe_load(mf)
            assert yamldict["build"]["noarch"] == "generic"
            assert yamldict["build"]["number"] == 0
            assert yamldict["extra"]["authors"] == "me"
            assert yamldict["extra"]["extra-files"] == []   
            assert yamldict["package"]["name"] == ggd_package
            assert yamldict["package"]["version"] == "1"
            assert yamldict["requirements"]["build"] == ['gsort', 'htslib', 'zlib']
            assert yamldict["requirements"]["run"] == ['gsort', 'htslib', 'zlib']
            assert yamldict["source"]["path"] == "."
            assert yamldict["about"]["identifiers"]["genome-build"] == "hg19"
            assert yamldict["about"]["identifiers"]["species"] == "Homo_sapiens"
            assert yamldict["about"]["keywords"] == ['gaps','region']
            assert yamldict["about"]["summary"] == "Assembly gaps from UCSC"
            assert yamldict["about"]["tags"]["data-version"] == "27-Apr-2009"
            assert yamldict["about"]["tags"]["data-provider"] == "UCSC"
            assert yamldict["about"]["tags"]["ggd-channel"] == "genomics"

    except IOError as e:
        print(e)
        assert False

    ## Test post-link.sh
    try:
        with open(new_postlink_file, "r") as pf:
            recipe_dir = False
            pkd_dir = False
            dir_env_var = False
            file_env_var = False
            run_recipe_script = False
            file_extention = False
            rename_data = False
            for line in pf:
                ### Check the assignment of RECIPE_DIR
                if "RECIPE_DIR=" in line:
                    assert line.strip() == """export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg19/hg19-test-gaps-ucsc-v1/1""" or line.strip() == """export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg19/hg19-test-gaps-ucsc-v1/1"""
                    recipe_dir = True
                ### Check the assigning of PKG_DIR to conform with proper file filtering for Linus and macOSX
                if "PKG_DIR=" in line:
                    assert line.strip() == """PKG_DIR=`find "$CONDA_ROOT/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`"""
                    pkd_dir = True

                ### Check enivornment variable setting 
                if "recipe_env_dir_name=" in line:
                    assert line.strip() == """recipe_env_dir_name="ggd_hg19-test-gaps-ucsc-v1_dir" """.strip() \
                    or line.strip() == """recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g' | sed 's/\./_/g')" """.strip() \
                    or line.strip() == """echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh"""
                    dir_env_var = True

                if "recipe_env_file_name=" in line:
                    assert line.strip() == """recipe_env_file_name="ggd_hg19-test-gaps-ucsc-v1_file" """.strip() \
                    or line.strip() == """recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g' | sed 's/\./_/g')" """.strip() \
                    or line.strip() == """if [[ ! -z "${recipe_env_file_name:-}" ]] """.strip() \
                    or line.strip() == """echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh"""
                    file_env_var = True

                #### Check that the recipe is being run
                if "bash $PKG_DIR" in line:
                    assert line.strip() == """(cd $RECIPE_DIR && bash $PKG_DIR/info/recipe/recipe.sh)"""
                    run_recipe_script = True

                ### Check taht the extention for the data files is being extracted 
                if "ext=" in line:
                    assert line.strip() == """ext="${f#*.}" """.strip()
                    file_extention = True

                ### Check that the data file names are replaced with the ggd package name, but the extentions are kept
                if "(mv $f" in line:
                    assert line.strip() == """(mv $f "hg19-test-gaps-ucsc-v1.$ext")"""
                    rename_data = True
            
            assert recipe_dir
            assert pkd_dir
            assert dir_env_var
            assert file_env_var
            assert run_recipe_script
            assert file_extention
            assert rename_data

    except IOError as e:
        print(e)
        assert False

    os.remove(new_recipe_file)
    os.remove(new_metayaml_file)
    os.remove(new_postlink_file)
    os.rmdir(ggd_package)
    


def test_make_bash_all_params():
    """
    Test the main method of ggd make-recipe
    """

    recipe = CreateRecipe(

    """
    hg19-test-gaps2-ucsc-v1:
        recipe.sh: |

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg19/hg19.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg19/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > gaps.bed.gz

            tabix gaps.bed.gz 

    """, from_string=True)

    recipe.write_recipes() 

    ggd_package = "hg19-test-gaps2-ucsc-v1"

    recipe_file = os.path.join(recipe.recipe_dirs["hg19-test-gaps2-ucsc-v1"],"recipe.sh")

    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=['vt','samtools','bedtools'], extra_file=['not.a.real.extra.file'], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps2', platform='none', script=recipe_file, species='Homo_sapiens', summary='Assembly gaps from UCSC')

    assert make_bash.make_bash((),args) 

    new_recipe_file = os.path.join("./", ggd_package, "recipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_metayaml_file = os.path.join("./", ggd_package, "meta.yaml") 
    assert os.path.exists(new_metayaml_file)
    assert os.path.isfile(new_metayaml_file)
    new_postlink_file = os.path.join("./", ggd_package, "post-link.sh") 
    assert os.path.exists(new_postlink_file)
    assert os.path.isfile(new_postlink_file)

    ## Test meta.yaml
    try:
        with open(new_metayaml_file, "r") as mf:
            yamldict = yaml.safe_load(mf)
            assert yamldict["build"]["number"] == 0
            assert "noarch" not in yamldict["build"].keys()
            assert yamldict["extra"]["authors"] == "me"
            assert yamldict["extra"]["extra-files"] == ['{}.a.real.extra.file'.format(ggd_package)]   
            assert yamldict["package"]["name"] == ggd_package
            assert yamldict["package"]["version"] == "1"
            assert yamldict["requirements"]["build"] == ['bedtools', 'gsort', 'htslib', 'samtools', 'vt', 'zlib']
            assert yamldict["requirements"]["run"] == ['bedtools', 'gsort', 'htslib', 'samtools', 'vt', 'zlib']
            assert yamldict["source"]["path"] == "."
            assert yamldict["about"]["identifiers"]["genome-build"] == "hg19"
            assert yamldict["about"]["identifiers"]["species"] == "Homo_sapiens"
            assert yamldict["about"]["keywords"] == ['gaps','region']
            assert yamldict["about"]["summary"] == "Assembly gaps from UCSC"
            assert yamldict["about"]["tags"]["data-version"] == "27-Apr-2009"
            assert yamldict["about"]["tags"]["ggd-channel"] == "genomics"

    except IOError as e:
        print(e)
        assert False

    os.remove(new_recipe_file)
    os.remove(new_metayaml_file)
    os.remove(new_postlink_file)
    os.rmdir(ggd_package)


def test_make_bash_meta_yaml_key_order():
    """
    Test the main method of ggd make-recipe
    """

    recipe = CreateRecipe(

    """
    hg19-test-gaps3-ucsc-v1:
        recipe.sh: |

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg19/hg19.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg19/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > gaps.bed.gz

            tabix gaps.bed.gz 

    """, from_string=True)

    recipe.write_recipes() 

    ggd_package = "hg19-test-gaps3-ucsc-v1"

    recipe_file = os.path.join(recipe.recipe_dirs["hg19-test-gaps3-ucsc-v1"],"recipe.sh")

    args = Namespace(authors='me', channel='genomics', command='make-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=['vt','samtools','bedtools'], extra_file=['not.a.real.extra.file'], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps3', platform='none', script=recipe_file, species='Homo_sapiens', summary='Assembly gaps from UCSC')

    assert make_bash.make_bash((),args) 

    new_recipe_file = os.path.join("./", ggd_package, "recipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_metayaml_file = os.path.join("./", ggd_package, "meta.yaml") 
    assert os.path.exists(new_metayaml_file)
    assert os.path.isfile(new_metayaml_file)
    new_postlink_file = os.path.join("./", ggd_package, "post-link.sh") 
    assert os.path.exists(new_postlink_file)
    assert os.path.isfile(new_postlink_file)

    ## Test that the keys in the meta.yaml file are in the correct order. 
    ## Conda-build requires a strict order: https://github.com/conda/conda-build/issues/3267
    try:
        ref_keys = ["build","extra","package","requirements","source","about"]
        index = 0
        with open(new_metayaml_file, "r") as mf:
            for item in mf:
                item = item.strip().replace(":","")
                if item in ref_keys:
                    assert ref_keys[index] == item
                    ref_keys[index] = "Done"
                    index += 1
        assert index-1 == 5 ## Index - 1 because an additional 1 was added at the end. (Only index 0-5 exists)

    except IOError as e:
        print(e)
        assert False

    os.remove(new_recipe_file)
    os.remove(new_metayaml_file)
    os.remove(new_postlink_file)
    os.rmdir(ggd_package)




