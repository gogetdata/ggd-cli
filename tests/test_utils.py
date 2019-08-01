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
from helpers import CreateRecipe, uninstall_hg19_gaps_ucsc_v1
from ggd import utils

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO

#---------------------------------------------------------------------------------------------------------
## enable socket
#---------------------------------------------------------------------------------------------------------
from pytest_socket import disable_socket, enable_socket

def pytest_disable_socket():
    disable_socket()

def pytest_enable_socket():
    enable_socket()


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
    pytest_enable_socket()

    ## Get species list using the update repo option
    species = utils.get_species(update_files=True)
    species2 = utils.get_species()
    assert species == species2
    assert "Homo_sapiens" in species
    assert "Mus_musculus" in species
    assert "Drosophila_melanogaster" in species
    assert "Canis_familiaris" in species
    assert "Danio_rerio" in species 
    assert len(species) == 5

    ## Test not_updating repo
    species = utils.get_species(update_files=False)
    assert species == species2
    assert "Homo_sapiens" in species
    assert "Mus_musculus" in species
    assert "Drosophila_melanogaster" in species
    assert "Canis_familiaris" in species
    assert "Danio_rerio" in species 
    assert len(species) == 5

    ## Test that the full dictionary with species as keys and build as values is returned
    species_dict = utils.get_species(update_files=False,full_dict=True)
    species = species_dict.keys()
    assert "Homo_sapiens" in species
    assert "Mus_musculus" in species
    assert "Drosophila_melanogaster" in species
    assert "Canis_familiaris" in species
    assert "Danio_rerio" in species 
    assert len(species) == 5

    for key in species:
        assert len(species_dict[key]) > 0

    ### Test some builds are in the dict
    assert "hg19" in species_dict["Homo_sapiens"]
    assert "hg38" in species_dict["Homo_sapiens"]
    assert "GRCh37" in species_dict["Homo_sapiens"]
    assert "GRCh38" in species_dict["Homo_sapiens"]

    ## Test genomic metadata file path
    assert os.path.exists(os.path.expanduser("~/.config/ggd-info/genome_metadata/species_to_build.json"))

    
def test_get_ggd_channels():
    """
    Test the get_ggd_channels function to properly return the ggd channels 
    """
    pytest_enable_socket()

    channels = utils.get_ggd_channels()
    assert "genomics" in channels
    assert "alpha" not in channels
    assert "dev" not in channels
    assert len(channels) == 1

    ## Test genomic metadata file path
    assert os.path.exists(os.path.expanduser("~/.config/ggd-info/genome_metadata/ggd_channels.json"))


def test_get_channel_data():
    """
    Test that the get_channel_data correctly gets provides a path to the channel data file on your system
    """
    pytest_enable_socket()

    ## Test a real channel
    channel = "genomics"
    channeldata_path = utils.get_channel_data(channel)
    assert os.path.exists(channeldata_path)
    with open(channeldata_path, "r") as j:
        cdata_dict = json.load(j)
        assert "hg19-gaps-ucsc-v1" in cdata_dict["packages"].keys()

    ## Test a fake channel
    channel = "fake"
    try:
        channeldata_path = utils.get_channel_data(channel)
    except:
        pass
    try:
        with open(channeldata_path, "r") as j:
            cdata_dict = json.load(j)
        assert False ## should not be able to load
    except:
        pass

    ## Test channel metadata file path
    assert os.path.exists(os.path.expanduser("~/.config/ggd-info/channeldata/genomics/channeldata.json"))


def test_get_channeldata_url():
    """
    Test the get_channeldata_url properly returns the url to the channel data
    """
    pytest_enable_socket()
    
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
    pytest_enable_socket()

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
    pytest_enable_socket()

    output = utils.check_output(["ls", "-lh"])
    assert isinstance(output, str) or isinstance(output, unicode) 


def test__to_str():
    """
    test that _to_str converts a byte into a string correctly
    """
    pytest_enable_socket()
    
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
    pytest_enable_socket()

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

    builds2 = utils.get_builds("*")
    assert "hg19" in builds2 and "hg38" in builds2 and "GRCh37" in builds2 and "GRCh38" in builds2 and "mm10" in builds2 and \
    "mm9" in builds2 and "dm3" in builds2 and "dm6" in builds2 and "canFam3" in builds2 and "danRer10" in builds2 and \
    "danRer11" in builds2 and "GRCz10" in builds2 and "GRCz11" in builds2
    assert len(builds2) == 13

    ## Test genomic metadata file path
    assert os.path.exists(os.path.expanduser("~/.config/ggd-info/genome_metadata/build_to_species.json"))


def test_check_for_internet_connection():
    """
    Method to check that their is an internet connection
    """
    pytest_enable_socket()

    assert utils.check_for_internet_connection() == True
    assert utils.check_for_internet_connection(3) == True
    
    pytest_disable_socket()
    assert utils.check_for_internet_connection() == False
    pytest_enable_socket()


def test_update_channel_data_files():
    """
    Test that the update_channel_data_files function correctly updates the local copy of the channeldata.json file
    """
    pytest_enable_socket()


    file_path = os.path.expanduser("~/.config/ggd-info/channeldata")
    if os.path.exists(file_path):
        shutil.rmtree(file_path)

    assert os.path.exists(file_path) == False


    channel = "Fake-channel"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        utils.update_channel_data_files(channel)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("The 'Fake-channel' channel is not a ggd conda channel") 

    channel = "genomics"
    assert utils.update_channel_data_files(channel) == True
    
    assert os.path.exists(file_path)
    assert os.path.exists(os.path.join(file_path,channel,"channeldata.json"))


def test_update_genome_metadata_files():
    """
    Test that the update_genome_metadata_files function properly updates the local species_to_build.json,
     build_to_species.json, and ggd_channel.json files
    """
    pytest_enable_socket()

    file_path = os.path.expanduser("~/.config/ggd-info/genome_metadata")
    if os.path.exists(file_path):
        shutil.rmtree(file_path)

    ## Test that there is no files/path
    assert os.path.exists(file_path) == False

    ## Test that running the update creates the files and file path
    assert utils.update_genome_metadata_files()
    assert os.path.exists(file_path)
    assert os.path.exists(os.path.join(file_path,"build_to_species.json"))
    assert os.path.exists(os.path.join(file_path,"species_to_build.json"))
    assert os.path.exists(os.path.join(file_path,"ggd_channels.json"))


def test_validate_build():
    """
    Test that validate_build function properly handles different builds with different species
    """
    pytest_enable_socket()

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
    pytest_enable_socket()

    croot = sp.check_output(['conda', 'info', '--root'])
    assert croot.decode("utf8").strip() == utils.conda_root().strip()


def test_get_conda_env():
    """
    Test that the get_conda_env function properly identifies the current conda env 
    """
    pytest_enable_socket()

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
    pytest_enable_socket()

    ## Test that the base environemnet is returned
    conda_env = utils.active_conda_env()
    assert conda_env.strip() == "base"

    ## TODO: Add a test to check a different environment is active

def test_prefix_in_conda():
    """
    Test that the prefis in conda properly identifes a prefix that is in the conda enviroment, and those that are not
    """
    pytest_enable_socket()

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


def test_get_conda_package_list():
    """
    Test that the get_conda_package_list properly returns the correct installed packages from the conda list
    """
    pytest_enable_socket()

    ## Get the available ggd data packages in the ggd-genomics channel
    channeldata_path = utils.get_channel_data("genomics")
    cdata_dict = {}
    with open(channeldata_path, "r") as j:
        cdata_dict = json.load(j)

    ## Test the current environment
    current_packages = utils.get_conda_package_list(utils.conda_root())

    for p_name, p_info in current_packages.items():
        assert p_info["channel"] == "ggd-genomics"
        assert p_name in cdata_dict["packages"].keys() 
        assert p_info["name"] in cdata_dict["packages"].keys() 

    assert len(current_packages) > 0 


    ## Test a different environment
    environments = [os.path.join(x+"/") for x in utils.check_output(["conda", "info", "--env"]).strip().replace("*","").replace("\n"," ").split(" ") if os.path.isdir(x)]
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env")
    sp.check_output(["conda", "create", "--name", "temp_env"])

    ### Install a pacakge into the temp_env
    ggd_package = "hg19-pfam-domains-ucsc-v1"
    sp.check_output(["ggd", "install", "--prefix", temp_env, ggd_package])

    temp_env_packages = utils.get_conda_package_list(temp_env)

    assert ggd_package in temp_env_packages.keys()
    assert temp_env_packages[ggd_package]["channel"] == "ggd-genomics"
    assert temp_env_packages[ggd_package]["name"] == ggd_package
    assert len(temp_env_packages) == 1 ## Only 1 ggd package should be installed in this env

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env"])

    ## TODO: add regex test, where a pacakge is listed based off the prefix and pattern (regex) provided



def test_bypass_satsolver_on_install():
    """
    Test that the bypass_satsolver_on_install function properly installs a cached packages and bypasses sat solving
    """
    pytest_enable_socket()

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




