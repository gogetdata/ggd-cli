#---------------------------------------------------------------------------------------------------------
## Import statments
#---------------------------------------------------------------------------------------------------------
from __future__ import print_function
import os
import sys
import subprocess as sp
import pytest
import yaml
import tempfile
import requests
import argparse
import re
import time
import json
import shutil
from copy import deepcopy
from argparse import Namespace
from argparse import ArgumentParser
import glob
import contextlib
import tarfile
from helpers import CreateRecipe, uninstall_hg19_gaps_ucsc_v1, install_hg19_gaps_ucsc_v1
from ggd import utils
from ggd import install
from ggd import list_pkg_info, list_files, show_env, make_bash, uninstall


if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO



#---------------------------------------------------------------------------------------------------------
## Disable and enable socket
#---------------------------------------------------------------------------------------------------------
from pytest_socket import disable_socket, enable_socket

def pytest_disable_socket():
    disable_socket()

def pytest_enable_socket():
    enable_socket()


#---------------------------------------------------------------------------------------------------------
## Test Label
#---------------------------------------------------------------------------------------------------------

TEST_LABEL = "internet-free-test"

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
# Unit test for Internet Free context 
#-----------------------------------------------------------------------------------------------------------------------

def test_check_for_internet_connection_internet_free():
    """
    Test the check_for_internet_connection function when the socket is disabled. 
        (utils)
    """
    pytest_disable_socket()
    assert utils.check_for_internet_connection() == False

    pytest_enable_socket()
    assert utils.check_for_internet_connection()


def test_show_env_internet_free():
    """
    test the show-env ggd call can run an internet free context
        (show-env)
    """

    ## Install hg19-gaps
    try:
        pytest_enable_socket()
        install_hg19_gaps_ucsc_v1()
    except:
        pass

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    args = Namespace(command='show-env', pattern=None)
    dir_env_var_name = "$ggd_hg19_gaps_ucsc_v1_dir"
    file_env_var_name = "$ggd_hg19_gaps_ucsc_v1_file"

    ## Test show_env
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
       show_env.show_env((),args)
    output = temp_stdout.getvalue().strip()
    assert (dir_env_var_name in output)
    assert (file_env_var_name in output)


def test_in_ggd_channel_internet_free():
    """
    Test the in_ggd_channel function in list-files in an internet free context
        (list-files)
    """

    ## Install hg19-gaps
    try:
        pytest_enable_socket()
        install_hg19_gaps_ucsc_v1()
    except:
        pass
    
    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Test that in_ggd_channel properly returns the species, genome-build, and versoin if it is in the channel
    ggd_package = "hg19-gaps-ucsc-v1"
    channel = "genomics"
    species, build, version = list_files.in_ggd_channel(ggd_package, channel)
    assert species == "Homo_sapiens"
    assert build == "hg19"
    assert version == "1"
    
    ## test that in_ggd_channel properly handels bad channels 
    ggd_package = "hg19-gaps-ucsc-v1"
    channel = "not_a_real_channel"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.in_ggd_channel(ggd_package, channel)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## check that the exit code is 1
    
    ## test that in_ggd_channel properly handels bad recipe name 
    ggd_package = "NOT_A_REAL_PACKAGE_NAME"
    channel = "genomics"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.in_ggd_channel(ggd_package, channel)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## check that the exit code is 1


def test_list_files_internet_free():
    """
    test the list_files function in list-files in an internet free context
        (list-files)
    """

    ## Install hg19-gaps
    try:
        pytest_enable_socket()
        install_hg19_gaps_ucsc_v1()
    except:
        pass
    
    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Test list-files
    ggd_package = "hg19-gaps-ucsc-v1"
    file1 = "{}.bed.gz".format(ggd_package)
    file2 = "{}.bed.gz.tbi".format(ggd_package)

    ##Test that the correct file paths are returned 
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=None, prefix=None, species=None, version=None)
    
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_files.list_files((),args)
    output = str(temp_stdout.getvalue().strip()) 
    assert re.search(file1+"$", sorted(output.split("\n"))[0])
    assert re.search(file2+"$", sorted(output.split("\n"))[1])
    assert len(output.split("\n")) == 2

    ##Test that the correct file paths are returned with the genome_build key set
    args = Namespace(channel='genomics', command='list-files', genome_build="hg19", name=ggd_package, pattern=None, prefix=None, species=None, version=None)
    
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_files.list_files((),args)
    output = str(temp_stdout.getvalue().strip()) 
    assert re.search(file1+"$", sorted(output.split("\n"))[0])
    assert re.search(file2+"$", sorted(output.split("\n"))[1])
    assert len(output.split("\n")) == 2

    ##Test that the correct file paths are returned with the species key set
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=None, prefix=None, species="Homo_sapiens", version=None)
    
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_files.list_files((),args)
    output = str(temp_stdout.getvalue().strip()) 
    assert re.search(file1+"$", sorted(output.split("\n"))[0])
    assert re.search(file2+"$", sorted(output.split("\n"))[1])
    assert len(output.split("\n")) == 2

    ##Test that the correct file paths are returned with version  key set
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=None, prefix=None, species=None, version="1")

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_files.list_files((),args)
    output = str(temp_stdout.getvalue().strip()) 
    assert re.search(file1+"$", sorted(output.split("\n"))[0])
    assert re.search(file2+"$", sorted(output.split("\n"))[1])
    assert len(output.split("\n")) == 2

    ## Test that nothing is returned when a bad ggd package name is given
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name="NOT_a_real_package_name", pattern=None, prefix=None, species=None, version=None)
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.list_files((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## check that the exit code is 1

    ##Test that the function exits if a bad genome build is given
    args = Namespace(channel='genomics', command='list-files', genome_build="Bad_Build", name=ggd_package, pattern=None, species=None, prefix=None, version=None)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.list_files((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("3") ## check that the exit code is 1

    ##Test that the function exits if a bad species is given
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=None, prefix=None, species="Mus_musculus", version=None)
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.list_files((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("3") ## check that the exit code is 1

    ##Test that the function exits if a bad version is given
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=None, prefix=None, species=None, version="99999")
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.list_files((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## check that the exit code is 1

    ##Test that the function exits if a bad pattern is given
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern="BAD_PATTERN", prefix=None, species=None, version=None)
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.list_files((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## check that the exit code is 1


    ##Test that the function exits if a bad channel is given
    args = Namespace(channel='bad-channel', command='list-files', genome_build=None, name=ggd_package, pattern=None, prefix=None, species=None, version=None)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.list_files((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## check that the exit code is 1


def test_list_file_with_prefix_internet_free():
    """
    test the --prefix flag of list-files in a internet free context
        (list-files --prefix)
    """

    ## enable socket
    pytest_enable_socket()
    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env_internet_free")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env_internet_free"])
    try: 
        shutil.rmtree(temp_env)
    except Exception:
        pass 
    ## Create conda environmnet 
    sp.check_output(["conda", "create", "--name", "temp_env_internet_free"])

    ## Install ggd recipe using conda into temp_env
    ggd_package = "hg19-pfam-domains-ucsc-v1"
    install_args = Namespace(channel='genomics', command='install', debug=False, name=ggd_package, version='-1', prefix = temp_env)
    assert install.install((), install_args) == True 
    

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Test the list-files method can access info from the files in a different prefix
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=None, prefix=temp_env, species=None, version=None)

    file1 = "{}.bed12.bed.gz".format(ggd_package)
    file2 = "{}.bed12.bed.gz.tbi".format(ggd_package)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_files.list_files((),args)
    output = str(temp_stdout.getvalue().strip()) 
    assert file1 in  output
    assert file2 in  output
    assert temp_env in output
    assert len(output.split("\n")) == 2 


    ## Check output has correct file path
    ### Enable socket
    pytest_enable_socket()
    jdict = install.check_ggd_recipe(ggd_package,"genomics")
    species = jdict["packages"][ggd_package]["identifiers"]["species"]
    build = jdict["packages"][ggd_package]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_package]["version"]
    assert os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file1) in output
    assert os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file2) in output
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file1))
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file2))

    ## Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env_internet_free"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


def test_list_all_versions_internet_free():
    """
    Test the list_all_versions function for pkg-info in a internet free context
        (pkg-info)
    """

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False
    
    ## Test that all vresion of a hg19-gaps in the ggd-dev channel are properly listed

    ggd_package = "hg19-gaps"
    ggd_channel = "dev"

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.list_all_versions(ggd_package, ggd_channel)
    output = temp_stdout.getvalue().strip() 
    collect = False 
    header_list = [] 
    for line in output.strip().split("\n"):
        if "Name" in line and "Version" in line and "Build" in line and "Channel" in line:
            header_list = re.sub(r"\s+", "\t", line.strip()).split("\t") 
            collect = True 
        if collect:
            if ggd_package in line:
                line_list = re.sub(r"\s+", "\t", line.strip()).split("\t")
                assert ggd_package == line_list[header_list.index("Name") - 1] 
                assert "ggd-"+ggd_channel == line_list[header_list.index("Channel") -1 ] 
                assert "1" == line_list[header_list.index("Version") - 1] 
                assert "0" == line_list[header_list.index("Build") - 1] or "2" == line_list[header_list.index("Build") - 1] or "3" == line_list[header_list.index("Build") - 1]

    assert list_pkg_info.list_all_versions(ggd_package, ggd_channel) == True 


def test_check_if_ggd_recipe_internet_free():
    """
    test the check_if_ggd_recipe function in pkg-info in a internet free context
        (pkg-info)
    """
    
    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Test a normal package name and channel
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    assert list_pkg_info.check_if_ggd_recipe(ggd_package, ggd_channel) == True

    
def test_get_meta_yaml_info_internet_free(): 
    """
    test the get_meta_yaml_info function in pkg-info in an internet free context
        (pkg-info)
    """

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Test a recipe
    recipe = CreateRecipe(

        """
        fake-recipe:
            meta.yaml: |
                build:
                  binary_relocation: false
                  detect_binary_files_with_prefix: false
                  noarch: generic
                  number: 1
                extra:
                  authors: me
                package:
                  name: fake-recipe
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
                  summary: A fake recipe for testing 
                  tags:
                    data-version: Today
                    ggd-channel: genomics 

        """, from_string=True)

    recipe.write_recipes()
    ggd_package = "fake-recipe"
    ggd_channel = "genomics"
    meta_yaml_file = os.path.join(recipe.recipe_dirs[ggd_package],"meta.yaml")

    try:
        f = open(meta_yaml_file, "r")

        temp_stdout = StringIO()
        with redirect_stdout(temp_stdout):
            list_pkg_info.get_meta_yaml_info(f,ggd_package,ggd_channel)
        output = temp_stdout.getvalue().strip()
        lines = output.strip().split("\n")
        assert lines[0] == "GGD-Recipe: fake-recipe"
        assert lines[1] == "GGD-Channel: {}-{}".format("ggd",ggd_channel)
        assert lines[2] == "Summary: A fake recipe for testing"
        assert lines[3] == "Pkg Version: 1"
        assert lines[4] == "Pkg Build: 1"
        assert lines[5] == "Species: Homo_sapiens"
        assert lines[6] == "Genome Build: hg19"
        assert lines[7] == "Keywords: gaps, region"
        assert lines[8] == "Data Version: Today"
        conda_root = utils.conda_root()
        assert lines[9] == "Pkg File Path: {}/share/ggd/Homo_sapiens/hg19/fake-recipe/1".format(conda_root)
        assert lines[10] == "Pkg Files:"
        f.close()

        f = open(meta_yaml_file, "r")
        assert list_pkg_info.get_meta_yaml_info(f,ggd_package,ggd_channel) == True
        f.close()

    except IOError as e:
        print("IO Error")
        print(e)
        f.close()
        assert False
    except AssertionError as e:
        print("Assertion Error")
        print(e)
        f.close()
        raise AssertionError(e)
    except Exception as e:
        print(e)
        f.close()
        raise AssertionError(e)
    finally:
        f.close()


def test_print_recipe_internet_free():
    """
    Test the print_recipe fucntion in pkg-info in a internet free context
        (pkg-info)
    """

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Test print_recipe
    message = "TESTING THE CREATION OF A RECIPE SCRIPT"
    recipe = CreateRecipe(

        """
        TestRecipe:
            recipe.sh: |
                {}
        """.format(message), from_string=True)

    recipe.write_recipes()

    ggd_package = "TestRecipe"
    recipe_file = os.path.join(recipe.recipe_dirs[ggd_package],"recipe.sh")

    try:
        f = open(recipe_file, "r")

        temp_stdout = StringIO()
        with redirect_stdout(temp_stdout):
            list_pkg_info.print_recipe(f,ggd_package)
        output = temp_stdout.getvalue().strip()
        assert "{} recipe file:".format(ggd_package) in output
        assert message in output
        assert "NOTE: The recipe provided above outlines where the data was accessed and how it was processed" in output
        assert "GGD" not in output
        f.close()

        f = open(recipe_file, "r")
        assert list_pkg_info.print_recipe(f,ggd_package) == True

    except IOError as e:
        print("IO Error")
        print(e)
        f.close()
        assert False
    except AssertionError as e:
        print("Assertion Error")
        print(e)
        f.close()
        raise AssertionError(e)
    except Exception as e:
        print(e)
        f.close()
        raise AssertionError(e)
    finally:
        f.close()


def test_get_pkg_info_internet_free():
    """
    Test that get_pkg_info in pkg-info in a internet free context
        (pkg-info)
    """

    ## Install hg19-gaps
    try:
        pytest_enable_socket()
        install_hg19_gaps_ucsc_v1()
    except:
        pass

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Test a normal run that should pass
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    assert list_pkg_info.get_pkg_info(ggd_package, ggd_channel, False) == True

    ## Test that a uninstalled package is handled correctly 
    ggd_package = "Bad_package"
    ggd_channel = "genomics"

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.get_pkg_info(ggd_package, ggd_channel, False)
    output = temp_stdout.getvalue().strip()
    assert ggd_package+" is not downloaded on your system, or was downloaded incorrectly" in output
    assert list_pkg_info.get_pkg_info(ggd_package, ggd_channel, False) == False


def test_info_main_internet_free():
    """
    test the pkg-info main funtion in an internet free context
        (pkg-info)
    """

    ## Install hg19-gaps
    try:
        pytest_enable_socket()
        install_hg19_gaps_ucsc_v1()
    except:
        pass

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Normal run
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    args = Namespace(all_versions=False, channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=False)
    assert list_pkg_info.info((),args) == True

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.info((),args)
    output = temp_stdout.getvalue().strip()
    lines = output.strip().split("\n")
    assert lines[0] == "GGD-Recipe: {}".format(ggd_package)
    assert lines[1] == "GGD-Channel: {}-{}".format("ggd",ggd_channel)
    assert lines[5] == "Species: Homo_sapiens"
    assert lines[6] == "Genome Build: hg19"
    assert lines[7] == "Keywords: gaps, region, bed-file"
    assert lines[9] == "Cached: uploaded_to_aws"


def test_make_bash_internet_free():
    """
    Test the main method of ggd make-recipe in an internet free context
        (make-recipe)
    """

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

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
                    assert line.strip() == """PKG_DIR=`find "$CONDA_SOURCE_PREFIX/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`"""

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


def test_get_channeldata_internet_free():
    """
    Test teh get_channeldata function in uninstall in an internet free context
        (uninstall)
    """

    ## Install hg19-gaps
    try:
        pytest_enable_socket()
        install_hg19_gaps_ucsc_v1()
    except:
        pass

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Test normal run
    ggd_recipe = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    jdict = uninstall.get_channeldata(ggd_recipe,ggd_channel)
    assert ggd_recipe in jdict["packages"].keys()


def test_uninstall_internet_free():
    """
    Test the uninstall method in an internet free context 
        (uninstall)
    """

    ## Install hg19-gaps
    try:
        pytest_enable_socket()
        install_hg19_gaps_ucsc_v1()
    except:
        pass

    ## Check show-env in an internet free context
    pytest_disable_socket()
    ### Check that there is no interent 
    assert utils.check_for_internet_connection() == False

    ## Check non-failure uninstall command
    ggd_recipe = "hg19-gaps-ucsc-v1"
    args = Namespace(channel='genomics', command='uninstall', name=ggd_recipe)
    assert uninstall.uninstall((),args) == True

    #### Get jdict 
    ggd_channel = "genomics"
    jdict = uninstall.get_channeldata(ggd_recipe,ggd_channel)
    conda_root = utils.conda_root()

    ### Check that the files are not in the conda root
    version = jdict["packages"][ggd_recipe]["version"]
    check_list = sp.check_output(["find", conda_root, "-name", ggd_recipe+"-"+str(version)+"*"]).decode("utf8").strip().split("\n")
    for f in check_list:
        if conda_root in f:
            if conda_root+"/envs/" not in path:
                assert ggd_recipe+"-"+str(version) not in path

    #### Check data files were removed
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]
    path = os.path.join(conda_root,"share","ggd",species,build,ggd_recipe,version)
    assert glob.glob(path) == []
    try:
        os.listdir(path)
        assert False
    except OSError as e:
        if "No such file or directory" in str(e):
            pass
        else:
            assert False

    #### Check that the ggd package is no longer in the list of conda packages
    output = sp.check_output(["conda", "list", ggd_recipe])
    assert ggd_recipe not in str(output)


