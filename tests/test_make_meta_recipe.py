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
from ggd import make_meta_recipe
import oyaml

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO


#---------------------------------------------------------------------------------------------------------
## enable socket
#---------------------------------------------------------------------------------------------------------
from pytest_socket import enable_socket

def pytest_enable_socket():
    enable_socket()


#---------------------------------------------------------------------------------------------------------
## Test Label
#---------------------------------------------------------------------------------------------------------

TEST_LABEL = "ggd-make-meta-recipe-test"


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
    pytest_enable_socket()

    ## test that make_bash fails when a bad summary is provided
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "Please provide a thorough summary of the data package" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

        
    ## test that make_bash fails when a bad summary is provided
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary=' ',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
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
    pytest_enable_socket()


    ## test that make_bash fails when a bad name is provided
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing name
        assert "The recipe name is required" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

        
    ## test that make_bash fails when a bad name is provided
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name=' ', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[] )
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
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
    pytest_enable_socket()

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test.gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\".\" wildcard is not allowed in the recipe name" in str(e)
        assert "hg19-test.gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test?gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"?\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test?gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test*gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"*\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test*gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test[gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"[\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test[gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test]gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"]\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test]gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False


    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test{gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"{\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test{gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False


    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test}gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"}\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test}gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False


    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test!gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"!\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test!gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False


    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test+gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"+\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test+gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test^gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"^\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test^gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test$gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"$\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test$gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test(gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        ## Correctly raises an assetion error due to the missing summary
        assert "\"(\" wildcard is not allowed in the recipe name. Please rename the recipe." in str(e)
        assert "hg19-test(gaps-ucsc-v1" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## test that make_bash fails when a wild card is added to the name
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC", 
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test)gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
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
    pytest_enable_socket()

    ## test that make_bash fails when a bad genome build is provided
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], genome_build='hg09', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])

    try:
        temp_stderr = StringIO()
        with redirect_stderr(temp_stderr):
            make_meta_recipe.make_bash((),args)  
    except Exception as e:
        os.rmdir("{}-{}-{}-v{}".format("hg09","test-gaps","ucsc","1"))
        output = str(temp_stderr.getvalue().strip()) 
        assert "ERROR: genome-build: hg09 not found in github repo for the Homo_sapiens species" in output

        
    ## test that make_bash fails when a bad genome build is provided
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], genome_build='hgmm10', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])
    try:
        temp_stderr = StringIO()
        with redirect_stderr(temp_stderr):
            make_meta_recipe.make_bash((),args)  
    except Exception as e:
        os.rmdir("{}-{}-{}-v{}".format("hgmm10","test-gaps","ucsc","1"))
        output = temp_stderr.getvalue().strip() 
        assert "ERROR: genome-build: hgmm10 not found in github repo for the Homo_sapiens species" in output


def test_make_bash_test_bad_recipe():
    """
    Test the main method of ggd make-recipe
    """
    pytest_enable_socket()

    ## test that make_bash fails when a bad recipe is provided
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script='bad-recipe.sh', species='Homo_sapiens', summary='Assembly gaps from USCS',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        make_meta_recipe.make_bash((), args)
    os.rmdir("{}-{}-{}-v{}".format("hg19","test-gaps","ucsc","1"))
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1


def test_make_bash_missing_tags():
    """
    Test that there is an error when missing tags
    """ 
    pytest_enable_socket()

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
    
    ## Bad coordinate 
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script=recipe_file, species='Homo_sapiens', summary='Assembly gaps from USCS',
                        coordinate_base="2-based-exclusive", file_type= [],final_file=[], extra_scripts=[])

    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        assert "2-based-exclusive is not an acceptable genomic coordinate base" in str(e)
        print(str(e))
        pass 
    except Exception as e:
        print(e)
        assert False

    ## Emtpy data version
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='', data_provider="UCSC",
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script=recipe_file, species='Homo_sapiens', summary='Assembly gaps from USCS',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[],extra_scripts=[])
    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        assert "Please provide the version of the data this recipe curates" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    ## Empty data provider 
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="",
                        dependency=[], genome_build='hg19', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps', platform='noarch', script=recipe_file, species='Homo_sapiens', summary='Assembly gaps from USCS',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])

    try:
        assert make_meta_recipe.make_bash((),args)  
        assert False
    except AssertionError as e:
        assert "The data provider is required" in str(e)
        pass 
    except Exception as e:
        print(e)
        assert False

    if os.path.exists(os.path.join(os.getcwd(), "hg19-test-gaps-ucsc-v1")):
        os.rmdir("hg19-test-gaps-ucsc-v1")


def test_make_bash():
    """
    Test the main method of ggd make-recipe
    """
    pytest_enable_socket()

    recipe = CreateRecipe(

    """
    test-meta-recipe-ucsc-v1:
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

    ggd_package = "meta-recipe-test-metarecipe-ucsc-v1"

    recipe_file = os.path.join(recipe.recipe_dirs["test-meta-recipe-ucsc-v1"],"recipe.sh")

    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=[], genome_build='meta-recipe', package_version='1', keyword=['gaps', 'region'], 
                        name='test-metarecipe', platform='noarch', script=recipe_file, species='meta-recipe', summary='some meta-recipe',
                        coordinate_base="0-based-inclusive", file_type= [],final_file=[], extra_scripts=[])

    assert make_meta_recipe.make_bash((),args) 

    new_recipe_file = os.path.join("./", ggd_package, "recipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_meta_recipe_file = os.path.join("./", ggd_package, "metarecipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_metayaml_file = os.path.join("./", ggd_package, "meta.yaml") 
    assert os.path.exists(new_metayaml_file)
    assert os.path.isfile(new_metayaml_file)
    new_postlink_file = os.path.join("./", ggd_package, "post-link.sh") 
    assert os.path.exists(new_postlink_file)
    assert os.path.isfile(new_postlink_file)
    new_checksums_file = os.path.join("./", ggd_package, "checksums_file.txt")
    assert os.path.exists(new_checksums_file)
    assert os.path.isfile(new_checksums_file)

    ## Test meta.yaml
    try:
        with open(new_metayaml_file, "r") as mf:
            yamldict = yaml.safe_load(mf)
            assert yamldict["build"]["noarch"] == "generic"
            assert yamldict["build"]["number"] == 0
            assert yamldict["extra"]["authors"] == "me"
            assert yamldict["package"]["name"] == ggd_package
            assert yamldict["package"]["version"] == "1"
            assert yamldict["requirements"]["build"] == ['gsort', 'htslib', 'zlib']
            assert yamldict["requirements"]["run"] == ['gsort', 'htslib', 'zlib']
            assert yamldict["source"]["path"] == "."
            assert yamldict["about"]["identifiers"]["genome-build"] == "meta-recipe"
            assert yamldict["about"]["identifiers"]["species"] == "meta-recipe"
            assert yamldict["about"]["keywords"] == ['gaps','region']
            assert yamldict["about"]["summary"] == "some meta-recipe"
            assert yamldict["about"]["tags"]["genomic-coordinate-base"] == "0-based-inclusive"
            assert yamldict["about"]["tags"]["data-version"] == "27-Apr-2009"
            assert yamldict["about"]["tags"]["data-provider"] == "UCSC"
            assert yamldict["about"]["tags"]["file-type"] == []
            assert yamldict["about"]["tags"]["final-files"] == []
            assert yamldict["about"]["tags"]["final-file-sizes"] == {}
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
            set_new_name = False
            for line in pf:
                ## Check new name
                if "new_name=" in line:
                    assert line.strip() == '''new_name="$GGD_METARECIPE_ID-ucsc-v1"''' or line.strip() == '''new_name="$(echo $new_name | tr '[:upper:]' '[:lower:]')"''' or line.strip() == """#new_name=${new_name,,} Requires bash version >= 4.2"""
                    set_new_name = True
                ### Check the assignment of RECIPE_DIR
                if "RECIPE_DIR=" in line:
                    assert line.strip() == """export RECIPE_DIR=$CONDA_ROOT/share/ggd/meta-recipe/meta-recipe/$new_name/1""" or line.strip() == """export RECIPE_DIR=$env_dir/share/ggd/meta-recipe/meta-recipe/$new_name/1"""
                    recipe_dir = True
                ### Check the assigning of PKG_DIR to conform with proper file filtering for Linus and macOSX
                if "PKG_DIR=" in line:
                    assert line.strip() == """PKG_DIR=`find "$CONDA_SOURCE_PREFIX/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`"""

                    pkd_dir = True

                ### Check enivornment variable setting 
                if "recipe_env_dir_name=" in line:
                    assert line.strip() == '''recipe_env_dir_name="ggd_""$new_name""_dir"'''.strip() \
                    or line.strip() == """recipe_env_dir_name="$(echo "$recipe_env_dir_name" | sed 's/-/_/g' | sed 's/\./_/g')" """.strip() \
                    or line.strip() == """echo "export $recipe_env_dir_name=$RECIPE_DIR" >> $activate_dir/env_vars.sh"""
                    dir_env_var = True

                if "recipe_env_file_name=" in line:
                    assert line.strip() == '''recipe_env_file_name="ggd_""$new_name""_file"'''.strip() \
                    or line.strip() == '''recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g' | sed 's/\./_/g')"'''.strip() \
                    or line.strip() == """if [[ ! -z "${recipe_env_file_name:-}" ]] """.strip() \
                    or line.strip() == '''echo "export $recipe_env_file_name=$file_path" >> $activate_dir/env_vars.sh'''.strip()
                    file_env_var = True

                #### Check that the recipe is being run
                ##### Ensure that the appropriate env variables are there 
                ###### - $RECIPE_DIR
                ###### - $SCRIPTS_PATH
                ###### - $GGD_METARECIPE_ID
                ###### - $GGD_METARECIPE_ENV_VAR_FILE
                ###### - $GGD_METARECIPE_FINAL_COMMANDS_FILE
                if "bash $SCRIPTS_PATH/metarecipe.sh" in line:
                    assert line.strip() == """(cd $RECIPE_DIR && bash $SCRIPTS_PATH/metarecipe.sh $GGD_METARECIPE_ID $SCRIPTS_PATH "$GGD_METARECIPE_ENV_VAR_FILE" "$GGD_METARECIPE_FINAL_COMMANDS_FILE")"""
                    run_recipe_script = True

            assert recipe_dir
            assert pkd_dir
            assert dir_env_var
            assert file_env_var
            assert run_recipe_script
            assert set_new_name

    except IOError as e:
        print(e)
        assert False

    os.remove(new_recipe_file)
    os.remove(new_meta_recipe_file)
    os.remove(new_metayaml_file)
    os.remove(new_postlink_file)
    os.remove(new_checksums_file)
    os.rmdir(ggd_package)
    


def test_make_meta_recipe_all_params():
    """
    Test the main method of ggd make-meta-recipe
    """
    pytest_enable_socket()

    recipe = CreateRecipe(

    """
    test-meta-recipe2-ucsc-v1:
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

    ggd_package = "meta-recipe-test-metarecipe2-ucsc-v1"

    recipe_file = os.path.join(recipe.recipe_dirs["test-meta-recipe2-ucsc-v1"],"recipe.sh")

    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=['vt','samtools','bedtools'], genome_build='meta-recipe', package_version='1', keyword=['gaps', 'region'], 
                        name='test-metarecipe2', platform='none', script=recipe_file, species='meta-recipe', summary='some meta-recipe',
                        coordinate_base="1-based-inclusive", file_type= [],final_file=[], extra_scripts=[])

    assert make_meta_recipe.make_bash((),args) 

    new_recipe_file = os.path.join("./", ggd_package, "recipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_meta_recipe_file = os.path.join("./", ggd_package, "metarecipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_metayaml_file = os.path.join("./", ggd_package, "meta.yaml") 
    assert os.path.exists(new_metayaml_file)
    assert os.path.isfile(new_metayaml_file)
    new_postlink_file = os.path.join("./", ggd_package, "post-link.sh") 
    assert os.path.exists(new_postlink_file)
    assert os.path.isfile(new_postlink_file)
    new_checksums_file = os.path.join("./", ggd_package, "checksums_file.txt")
    assert os.path.exists(new_checksums_file)
    assert os.path.isfile(new_checksums_file)

    ## Test meta.yaml
    try:
        with open(new_metayaml_file, "r") as mf:
            yamldict = yaml.safe_load(mf)
            assert yamldict["build"]["number"] == 0
            assert "noarch" not in yamldict["build"].keys()
            assert yamldict["extra"]["authors"] == "me"
            assert yamldict["package"]["name"] == ggd_package
            assert yamldict["package"]["version"] == "1"
            assert yamldict["requirements"]["build"] == ['bedtools', 'gsort', 'htslib', 'samtools', 'vt', 'zlib']
            assert yamldict["requirements"]["run"] == ['bedtools', 'gsort', 'htslib', 'samtools', 'vt', 'zlib']
            assert yamldict["source"]["path"] == "."
            assert yamldict["about"]["identifiers"]["genome-build"] == "meta-recipe"
            assert yamldict["about"]["identifiers"]["species"] == "meta-recipe"
            assert yamldict["about"]["keywords"] == ['gaps','region']
            assert yamldict["about"]["summary"] == "some meta-recipe"
            assert yamldict["about"]["tags"]["genomic-coordinate-base"] == "1-based-inclusive"
            assert yamldict["about"]["tags"]["data-version"] == "27-Apr-2009"
            assert yamldict["about"]["tags"]["file-type"] == [] ## Should be converted to lower case
            assert yamldict["about"]["tags"]["final-files"] == [] 
            assert yamldict["about"]["tags"]["final-file-sizes"] == {} 
            assert yamldict["about"]["tags"]["ggd-channel"] == "genomics"




    except IOError as e:
        print(e)
        assert False

    os.remove(new_recipe_file)
    os.remove(new_meta_recipe_file)
    os.remove(new_metayaml_file)
    os.remove(new_postlink_file)
    os.remove(new_checksums_file)
    os.rmdir(ggd_package)


def test_make_meta_recipe_extra_scripts():
    """
    Test the main method of ggd make-meta-recipe
    """
    pytest_enable_socket()

    recipe = CreateRecipe(

    """
    test-meta-recipe2-ucsc-v1:
        recipe.sh: |

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg19/hg19.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg19/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > gaps.bed.gz

            tabix gaps.bed.gz 

        extra_script1.py: |
            "this is an extra script"

        extra_script2.sh: |
            "this is another extra script"

    """, from_string=True)

    recipe.write_recipes() 

    ggd_package = "meta-recipe-test-metarecipe2-ucsc-v1"

    recipe_file = os.path.join(recipe.recipe_dirs["test-meta-recipe2-ucsc-v1"],"recipe.sh")
    extra_script = os.path.join(recipe.recipe_dirs["test-meta-recipe2-ucsc-v1"],"extra_script1.py")
    extra_script2  = os.path.join(recipe.recipe_dirs["test-meta-recipe2-ucsc-v1"],"extra_script2.sh")

    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=['vt','samtools','bedtools'], genome_build='meta-recipe', package_version='1', keyword=['gaps', 'region'], 
                        name='test-metarecipe2', platform='none', script=recipe_file, species='meta-recipe', summary='some meta-recipe',
                        coordinate_base="1-based-inclusive", file_type= [],final_file=[], extra_scripts=[extra_script, extra_script2])

    assert make_meta_recipe.make_bash((),args) 

    new_recipe_file = os.path.join("./", ggd_package, "recipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_meta_recipe_file = os.path.join("./", ggd_package, "metarecipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_extra_script_file = os.path.join("./", ggd_package, "extra_script1.py") 
    assert os.path.exists(new_extra_script_file)
    assert os.path.isfile(new_extra_script_file)
    new_extra_script_file2 = os.path.join("./", ggd_package, "extra_script2.sh") 
    assert os.path.exists(new_extra_script_file2)
    assert os.path.isfile(new_extra_script_file2)
    new_metayaml_file = os.path.join("./", ggd_package, "meta.yaml") 
    assert os.path.exists(new_metayaml_file)
    assert os.path.isfile(new_metayaml_file)
    new_postlink_file = os.path.join("./", ggd_package, "post-link.sh") 
    assert os.path.exists(new_postlink_file)
    assert os.path.isfile(new_postlink_file)
    new_checksums_file = os.path.join("./", ggd_package, "checksums_file.txt")
    assert os.path.exists(new_checksums_file)
    assert os.path.isfile(new_checksums_file)

    os.remove(new_recipe_file)
    os.remove(new_meta_recipe_file)
    os.remove(new_extra_script_file)
    os.remove(new_extra_script_file2)
    os.remove(new_metayaml_file)
    os.remove(new_postlink_file)
    os.remove(new_checksums_file)
    os.rmdir(ggd_package)


def test_make_bash_meta_yaml_key_order():
    """
    Test the main method of ggd make-recipe
    """
    pytest_enable_socket()

    recipe = CreateRecipe(

    """
    another-meta-recipe-ucsc-v1:
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

    ggd_package = "meta-recipe-another-metarecipe-ucsc-v1"

    recipe_file = os.path.join(recipe.recipe_dirs["another-meta-recipe-ucsc-v1"],"recipe.sh")

    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=['vt','samtools','bedtools'], genome_build='meta-recipe', package_version='1', keyword=['gaps', 'region'], 
                        name='another-metarecipe', platform='none', script=recipe_file, species='meta-recipe', summary='Assembly gaps from UCSC',
                        coordinate_base="0-based-inclusive", file_type= ["Bed"], final_file=["hg19-test-gaps3-ucsc-v1.bed.gz", "hg19-test-gaps3-ucsc-v1.bed.gz.tbi"], extra_scripts=[])

    assert make_meta_recipe.make_bash((),args) 

    new_recipe_file = os.path.join("./", ggd_package, "recipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_metarecipe_file = os.path.join("./", ggd_package, "metarecipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_metayaml_file = os.path.join("./", ggd_package, "meta.yaml") 
    assert os.path.exists(new_metayaml_file)
    assert os.path.isfile(new_metayaml_file)
    new_postlink_file = os.path.join("./", ggd_package, "post-link.sh") 
    assert os.path.exists(new_postlink_file)
    assert os.path.isfile(new_postlink_file)
    new_checksums_file = os.path.join("./", ggd_package, "checksums_file.txt")
    assert os.path.exists(new_checksums_file)
    assert os.path.isfile(new_checksums_file)

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
    os.remove(new_metarecipe_file)
    os.remove(new_metayaml_file)
    os.remove(new_postlink_file)
    os.remove(new_checksums_file)
    os.rmdir(ggd_package)


def test_make_bash_meta_yaml_ggd_dependency():
    """
    Test the main method of ggd make-meta-recipe
    """
    pytest_enable_socket()

    recipe = CreateRecipe(

    """
    more-meta-recipe-ucsc-v1:
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

    ggd_package = "meta-recipe-test-gaps4-ucsc-v1"

    recipe_file = os.path.join(recipe.recipe_dirs["more-meta-recipe-ucsc-v1"],"recipe.sh")

    ## grch37-gene-features-ensembl-v1 as a dependency
    args = Namespace(authors='me', channel='genomics', command='make-meta-recipe', data_version='27-Apr-2009', data_provider="UCSC",
                        dependency=['grch37-gene-features-ensembl-v1','hg38-chrom-mapping-ensembl2ucsc-ncbi-v1','vt','samtools','bedtools'], genome_build='meta-recipe', package_version='1', keyword=['gaps', 'region'], 
                        name='test-gaps4', platform='none', script=recipe_file, species='meta-recipe', summary='some meta-recipe',
                        coordinate_base="0-based-inclusive", file_type= ["Bed"], final_file=["hg19-test-gaps4-ucsc-v1.bed.gz", "hg19-test-gaps4-ucsc-v1.bed.gz.tbi"],extra_scripts=[])

    assert make_meta_recipe.make_bash((),args) 

    new_recipe_file = os.path.join("./", ggd_package, "recipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_metarecipe_file = os.path.join("./", ggd_package, "metarecipe.sh") 
    assert os.path.exists(new_recipe_file)
    assert os.path.isfile(new_recipe_file)
    new_metayaml_file = os.path.join("./", ggd_package, "meta.yaml") 
    assert os.path.exists(new_metayaml_file)
    assert os.path.isfile(new_metayaml_file)
    new_postlink_file = os.path.join("./", ggd_package, "post-link.sh") 
    assert os.path.exists(new_postlink_file)
    assert os.path.isfile(new_postlink_file)
    new_checksums_file = os.path.join("./", ggd_package, "checksums_file.txt")
    assert os.path.exists(new_checksums_file)
    assert os.path.isfile(new_checksums_file)

    ## Test meta.yaml has an ggd dependency in the run requirements and not the build requirements
    try:
        with open(new_metayaml_file, "r") as mf:
            yamldict = yaml.safe_load(mf)
            assert yamldict["requirements"]["build"] == ['bedtools', 'gsort', 'htslib', 'samtools', 'vt', 'zlib']
            assert "grch37-gene-features-ensembl-v1" not in yamldict["requirements"]["build"]
            assert "hg38-chrom-mapping-ensembl2ucsc-ncbi-v1" not in yamldict["requirements"]["build"]
            assert yamldict["requirements"]["run"] == ['bedtools', 'grch37-gene-features-ensembl-v1', 'gsort', 'hg38-chrom-mapping-ensembl2ucsc-ncbi-v1', 'htslib', 'samtools', 'vt', 'zlib'] 
            assert "grch37-gene-features-ensembl-v1" in yamldict["requirements"]["run"]
            assert "hg38-chrom-mapping-ensembl2ucsc-ncbi-v1" in yamldict["requirements"]["run"]

    except IOError as e:
        print(e)
        assert False

    os.remove(new_recipe_file)
    os.remove(new_metarecipe_file)
    os.remove(new_metayaml_file)
    os.remove(new_postlink_file)
    os.remove(new_checksums_file)
    os.rmdir(ggd_package)


