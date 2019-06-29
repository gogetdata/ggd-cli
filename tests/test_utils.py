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
import json
from copy import deepcopy
from argparse import Namespace
from argparse import ArgumentParser
import glob
import contextlib
import tarfile
from helpers import CreateRecipe, uninstall_hg19_gaps_ucsc_v1
from ggd import utils

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO


#---------------------------------------------------------------------------------------------------------
## Test Label
#---------------------------------------------------------------------------------------------------------

TEST_LABEL = "utils-test"

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
# Unit test for utils 
#-----------------------------------------------------------------------------------------------------------------------
    
def test_get_species():
    """
    Test the get_species method for the utils function in ggd
    """

    ## Get species list using the update repo option
    species = utils.get_species(update_repo=True)
    species2 = utils.get_species()
    assert species == species2
    assert "Homo_sapiens" in species
    assert "Mus_musculus" in species
    assert "Drosophila_melanogaster" in species
    assert "Canis_familiaris" in species
    assert "Danio_rerio" in species 
    assert len(species) == 5

    ## Test not_updating repo
    species = utils.get_species(update_repo=True)
    assert species == species2
    assert "Homo_sapiens" in species
    assert "Mus_musculus" in species
    assert "Drosophila_melanogaster" in species
    assert "Canis_familiaris" in species
    assert "Danio_rerio" in species 
    assert len(species) == 5

    
def test_get_ggd_channels():
    """
    Test the get_ggd_channels function to properly return the ggd channels 
    """

    channels = utils.get_ggd_channels()
    assert "genomics" in channels
    assert "alpha" not in channels
    assert "dev" not in channels
    assert len(channels) == 1


def test_get_channel_data():
    """
    Test that the get_channel_data correctly gets provides a path to the channel data file on your system
    """

    ## Test a real channel
    channel = "genomics"
    channeldata_path = utils.get_channel_data(channel)
    assert os.path.exists(channeldata_path)
    with open(channeldata_path, "r") as j:
        cdata_dict = json.load(j)
        assert "hg19-gaps-ucsc-v1" in cdata_dict["packages"].keys()

    ## Test a fake channel
    channel = "fake"
    channeldata_path = utils.get_channel_data(channel)
    assert os.path.exists(channeldata_path) == False
    try:
        with open(channeldata_path, "r") as j:
            cdata_dict = json.load(j)
        assert False ## should not be able to load
    except:
        pass


def test_get_channeldata_url():
    """
    Test the get_channeldata_url properly returns the url to the channel data
    """
    
    ## Test a good url
    for channel in utils.get_ggd_channels():
        url = utils.get_channeldata_url(channel)
        assert requests.get(utils.get_channeldata_url(channel)).json()
        

    ## test a bad url
    channel = "Not-a-ggd-channel"
    try:
        requests.get(utils.get_channeldata_url(channel)).json()
        assert False ## Should throw an exception because the url does not exists
    except:
        pass


def test_get_required_conda_version():
    """
    Test that get_required_conda_version correctly returns the required conda version for using ggd
    """

    conda_version = utils.get_required_conda_version()
    assert  conda_version != -1
    version_list = conda_version.strip().split(".")
    ## Test that the conda version is greater than or equal to 4.6.8. (4.6.8 is the oldest release where all tests passed and ggd was work.)
    ## As of 4/10/2019 the latest conda version that works with all tests passing is 4.6.12
    assert int(version_list[0]) == 4 ## Conda version == 4.*.*
    assert int(version_list[1]) == 7 ## Conda version == *.6.*
    assert int(version_list[2]) >= 5 ## Conda version >= *.*.8
    

def test_check_output():
    """
    Test the check_output function properly runs returns a proper string output
    """
    output = utils.check_output(["ls", "-lh"])
    assert isinstance(output, str) or isinstance(output, unicode) 


def test__to_str():
    """
    test that _to_str converts a byte into a string correctly
    """
    
    test_string = "A test string"

    if sys.version_info[0] == 3:
        byte_string = bytes(test_string, "utf8")
    elif sys.version_info[0] == 2:
        byte_string = bytes(test_string)
    
    assert isinstance(byte_string, bytes)
    assert isinstance(test_string, str)
    ## Test that the string is properly returned if it is not a byte string
    assert utils._to_str(test_string) == test_string
    ## Test the byte string is properly returned to a ascii string
    assert utils._to_str(byte_string) == test_string


def test_get_build():
    """
    Test the get_build function properly returns the builds for a species
    """

    for species in utils.get_species():
        builds = utils.get_builds(species)
        if species == "Homo_sapiens":
            assert len(builds) == 4
            assert "hg19" in builds
            assert "hg38" in builds
            assert "GRCh37" in builds
            assert "GRCh38" in builds
        elif species == "Mus_musculus":
            assert len(builds) == 2
            assert "mm10" in builds
            assert "mm9" in builds
        elif species == "Drosophila_melanogaster": 
            assert len(builds) == 2
            assert "dm3" in builds
            assert "dm6" in builds
        elif species == "Canis_familiaris":
            assert len(builds) == 1
            assert "canFam3" in builds
        elif species == "Danio_rerio":
            assert len(builds) == 4
            assert "danRer10" in builds
            assert "danRer11" in builds
            assert "GRCz10" in builds
            assert "GRCz11" in builds
        else:
            assert False


def test_update_metadata_local_repo():
    """
    Test that update_metadata_local_repo function properly updates the ggd metadata local repo 
    """

    utils.update_metadata_local_repo()
    assert os.path.exists(utils.LOCAL_REPO_DIR)
    assert os.path.exists(utils.METADATA_REPO_DIR)


def test_update_local_repo():
    """
    Test that update_local_repo function properly updates the ggd local repo 
    """

    utils.update_local_repo()
    assert os.path.exists(utils.LOCAL_REPO_DIR)
    assert os.path.exists(utils.RECIPE_REPO_DIR)


def test_validate_build():
    """
    Test that validate_build function properly handles different builds with different species
    """

    assert utils.validate_build("hg19","Homo_sapiens") == True
    assert utils.validate_build("mm10","Homo_sapiens") == False
    assert utils.validate_build("mm10","Mus_musculus") == True
    assert utils.validate_build("hg38","*") == True
    assert utils.validate_build("*","*") == True
    assert utils.validate_build("*","Homo_sapiens") == True


def test_conda_root():
    """
    Test that the conda_root function properly returns the conda root
    """

    croot = sp.check_output(['conda', 'info', '--root'])
    assert croot.decode("utf8").strip() == utils.conda_root().strip()


def test_get_conda_env():
    """
    Test that the get_conda_env function properly identifies the current conda env 
    """

    ## Test that the base environemnet is returned
    croot = sp.check_output(['conda', 'info', '--root'])
    conda_env, conda_path = utils.get_conda_env()
    assert conda_path.strip() == croot.decode("utf8").strip()
    assert conda_env.strip() == "base"

    ## TODO: Add a test to check a different environment is active

def test_active_conda_env():
    """
    Test the active_conda_env function properly returns the active environemnt 
    """

    ## Test that the base environemnet is returned
    conda_env = utils.active_conda_env()
    assert conda_env.strip() == "base"

    ## TODO: Add a test to check a different environment is active

def test_prefix_in_conda():
    """
    Test that the prefis in conda properly identifes a prefix that is in the conda enviroment, and those that are not
    """

    ## Test a bad env (environments not in base environment path)
    try:
        utils.prefix_in_conda(os.getcwd())
    except utils.CondaEnvironmentNotFound as e:
        assert "The prefix supplied is not a conda enviroment: {}".format(os.getcwd()) in str(e) 
    except Exception as e:
        assert False

    try:
        utils.prefix_in_conda("/Not/A/Real/Location")
    except utils.CondaEnvironmentNotFound as e:
        assert "The prefix supplied is not a conda enviroment: {}".format("/Not/A/Real/Location") in str(e) 
    except Exception as e:
        assert False

    try:
        utils.prefix_in_conda("current")
    except utils.CondaEnvironmentNotFound as e:
        assert "The prefix supplied is not a conda enviroment: {}".format("current") in str(e) 
    except Exception as e:
        assert False

    ## Test that the prefix is or is not in the environmnets   
    ### List of enviroments
    environments = [os.path.join(x+"/") for x in utils.check_output(["conda", "info", "--env"]).strip().replace("*","").replace("\n"," ").split(" ") if os.path.isdir(x)]
    base_env = min(environments)
    temp_env = os.path.join(base_env, "envs", "temp_env")

    try:
        utils.prefix_in_conda(temp_env)
    except utils.CondaEnvironmentNotFound as e:
        assert "The prefix supplied is not a conda enviroment: {}".format(temp_env) in str(e) 
    except Exception as e:
        assert False

    ## Test the prefix passes all checks, is in the base environment, is in the list of environments, and it is a directoyr
    #os.mkdir(temp_env) 
    sp.check_output(["conda", "create", "--name", "temp_env"])
    environments = [os.path.join(x+"/") for x in utils.check_output(["conda", "info", "--env"]).strip().replace("*","").replace("\n"," ").split(" ") if os.path.isdir(x)]

    for env in environments:
        assert utils.prefix_in_conda(env)

    ## Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env"])


def test_bypass_satsolver_on_install():
    """
    Test that the bypass_satsolver_on_install function properly installs a cached packages and bypasses sat solving
    """

    ## Test a bad install, bad recipe
    ggd_package = "Bad-package"
    ggd_channel = "ggd-genomics"

    try:
        utils.bypass_satsolver_on_install(ggd_package,conda_channel = ggd_channel)
        assert False
    except:
        pass


    ## Test a bad install, bad channel
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "ggd-not-a-ggd-channel"

    try:
        utils.bypass_satsolver_on_install(ggd_package,conda_channel = ggd_channel)
        assert False
    except:
        pass


    ## Test a good install
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "ggd-genomics"
    ### Unininstall
    uninstall_hg19_gaps_ucsc_v1()

    assert utils.bypass_satsolver_on_install(ggd_package,conda_channel = ggd_channel) == True




