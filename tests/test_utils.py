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
from helpers import CreateRecipe, install_hg19_gaps_ucsc_v1, uninstall_hg19_gaps_ucsc_v1
from ggd import utils
from ggd import install

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
    assert int(version_list[1]) == 8 ## Conda version == *.8.*
    assert int(version_list[2]) >= 2 ## Conda version >= *.*.2
    

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


def test_update_installed_pkg_metadata():
    """
    Test that the update_installed_pkg_metadata method correctly updates the ggd info metadata with installed packages
    """

    ## enable socket
    pytest_enable_socket()

    ggd_package = "hg19-gaps-ucsc-v1"

    ## Try to install ggd_package. If fails, most likely due to the fact that it is already installed
    try:
        install_hg19_gaps_ucsc_v1()
    except Exception:
        pass

    ggd_info_dir = os.path.join(utils.conda_root(),"share","ggd_info")

    ## Test normal run
    if os.path.isdir(ggd_info_dir):
        shutil.rmtree(ggd_info_dir)
    assert os.path.exists(ggd_info_dir) == False
    
    assert utils.update_installed_pkg_metadata() == True
    matches = [re.search(ggd_package+".+",x).group() for x in os.listdir(os.path.join(ggd_info_dir,"noarch")) if re.search(ggd_package,x) != None]
    assert len(matches) > 0
    with open(os.path.join(ggd_info_dir,"channeldata.json")) as jsonFile:
        jdict = json.load(jsonFile)
        assert ggd_package in jdict["packages"]
    assert os.path.exists(ggd_info_dir) == True


    ## Test add_package != None and remove_old == True
    ### add_package != None and remove_old == True should never happen. This would result in only 1 package in the metadata
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        utils.update_installed_pkg_metadata(add_packages=["hg19-gaps-ucsc-v1"],remove_old=True)
    output = temp_stdout.getvalue().strip() 
    assert ("Warning: You indicated to add a single package to ggd info metadata but also indicated to re-build the metadata. This would result in the single indicated package being the only package in the metadata" in output)
    assert ("The ggd info metadata will be re-built and all ggd packages will be added" in output)


    ## Test prefix not set:
    ### Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env9")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env9"])
    try: 
        shutil.rmtree(temp_env)
    except Exception:
        pass 
    ### Create conda environmnet 
    sp.check_output(["conda", "create", "--name", "temp_env9"])

    ### Install ggd recipe using conda into temp_env
    ggd_package2 = "hg19-pfam-domains-ucsc-v1"
    install_args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_package2], file=[], prefix = temp_env)
    assert install.install((), install_args) == True 

    ggd_info_dir2 = os.path.join(temp_env,"share","ggd_info")

    ## Test the installed created the ggd info metadata 
    matches = [re.search(ggd_package2+".+",x).group() for x in os.listdir(os.path.join(ggd_info_dir2,"noarch")) if re.search(ggd_package2,x) != None]
    assert len(matches) > 0
    with open(os.path.join(ggd_info_dir2,"channeldata.json")) as jsonFile:
        jdict = json.load(jsonFile)
        assert ggd_package2 in jdict["packages"]
    assert os.path.exists(ggd_info_dir2) == True

    ## remove ggd info metadata
    if os.path.isdir(ggd_info_dir2):
        shutil.rmtree(ggd_info_dir2)
    assert os.path.exists(ggd_info_dir2) == False

    ## Run the update with prefix set and check the prefix
    assert utils.update_installed_pkg_metadata(prefix=temp_env) == True
    matches = [re.search(ggd_package2+".+",x).group() for x in os.listdir(os.path.join(ggd_info_dir2,"noarch")) if re.search(ggd_package2,x) != None]
    assert len(matches) > 0
    with open(os.path.join(ggd_info_dir2,"channeldata.json")) as jsonFile:
        jdict = json.load(jsonFile)
        assert ggd_package2 in jdict["packages"]
    assert os.path.exists(ggd_info_dir2) == True

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env9"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


def test_check_conda_pkg_dir(): 
    """
    Test that the check_conda_pkg_dir correctly replaces an installed ggd .tar.bz2 if it has been removed from the conda pkg dir  
    """

    ## Test prefix not set:
    ### Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "check_pkg_info_dir")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "check_pkg_info_dir"])
    try: 
        shutil.rmtree(temp_env)
    except Exception:
        pass 
    ### Create conda environmnet 
    sp.check_output(["conda", "create", "--name", "check_pkg_info_dir"])

    ## Test for a info dir and pkg dir that do not exists
    try:
        utils.check_conda_pkg_dir(temp_env) 
    except OSError as e:
        assert "No such file or directory" in str(e)

    ### Install ggd recipe using conda into temp_env
    ggd_package = "hg19-pfam-domains-ucsc-v1"
    install_args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_package], file=[], prefix = temp_env)
    assert install.install((), install_args) == True 

    ## Check that there is no errors
    assert utils.check_conda_pkg_dir(temp_env) == True 


    ## Check a tar.bz2 file removed from conda pkg dir
    conda_pkg_dir = os.path.join(temp_env,"pkgs")
    installed_ggd_pkgs = utils.get_conda_package_list(temp_env)
    installed_pkg =  ggd_package + "-" + installed_ggd_pkgs[ggd_package]["version"] + "-"+ installed_ggd_pkgs[ggd_package]["build"] + ".tar.bz2" 

    ## Remove the pkg from the conda pkg dir 
    if os.path.exists(os.path.join(conda_pkg_dir,installed_pkg)):
        os.remove(os.path.join(conda_pkg_dir,installed_pkg))

    ## Test that when a pkg tar file does not exists in the conda pkg dir, ggd will replace it 
    assert os.path.exists(os.path.join(conda_pkg_dir,installed_pkg)) == False
    assert utils.check_conda_pkg_dir(temp_env) == True 
    assert os.path.exists(os.path.join(conda_pkg_dir,installed_pkg)) == True

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "check_pkg_info_dir"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


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
    assert conda_env.strip() == os.path.basename(croot).decode("utf8").strip()


    ## Test with conda_root() set as prefix
    conda_env, conda_path = utils.get_conda_env(prefix=utils.conda_root())
    assert conda_path.strip() == croot.decode("utf8").strip()
    assert conda_env.strip() == os.path.basename(croot).decode("utf8").strip()

    ### Test with environment name
    conda_env, conda_path = utils.get_conda_env(prefix=conda_env)
    assert conda_path.strip() == croot.decode("utf8").strip()
    assert conda_env.strip() == os.path.basename(croot).decode("utf8").strip()


    ## Test new environment set as prefix
    env_name = "test_croot"
    temp_env = os.path.join(utils.conda_root(), "envs", env_name)
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try: 
        shutil.rmtree(temp_env)
    except Exception:
        pass 

    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", env_name])

    ### Test with environment name
    conda_env, conda_path = utils.get_conda_env(prefix=env_name)
    assert conda_path.strip() == str(temp_env)
    assert conda_env.strip() == env_name

    ### Test with environment path
    conda_env, conda_path = utils.get_conda_env(prefix=temp_env)
    assert conda_path.strip() == str(temp_env)
    assert conda_env.strip() == env_name

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


def test_get_conda_prefix_path():
    """
    Test that get_conda_prefix_path() returns the correct prefix path 
    """

    pytest_enable_socket()

    ## Test Normal Run
    croot = utils.conda_root()
    croot_name = os.path.basename(croot)
    
    prefix_path = utils.get_conda_prefix_path(croot)
    assert prefix_path == croot

    prefix_path = utils.get_conda_prefix_path(croot_name)
    assert prefix_path == croot

    try:
        utils.get_conda_prefix_path("BAD_ENV")
    except utils.CondaEnvironmentNotFound as e:
        assert "The prefix supplied is not a conda enviroment: {}".format("BAD_ENV") in str(e) 
    except Exception as e:
        assert False


    ## Test different conda prefix
    env_name = "test_croot2"
    temp_env = os.path.join(utils.conda_root(), "envs", env_name)
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try: 
        shutil.rmtree(temp_env)
    except Exception:
        pass 

    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", env_name])

    prefix_path = utils.get_conda_prefix_path(temp_env)
    assert prefix_path == temp_env

    prefix_path = utils.get_conda_prefix_path(env_name)
    assert prefix_path == temp_env

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


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
    env_name = "temp_env"
    temp_env = os.path.join(utils.conda_root(), "envs", env_name)

    try:
        utils.prefix_in_conda(temp_env)
    except utils.CondaEnvironmentNotFound as e:
        assert "The prefix supplied is not a conda enviroment: {}".format(temp_env) in str(e) 
    except Exception as e:
        assert False

    ## Test the prefix passes all checks, is in the base environment, is in the list of environments, and it is a directoyr
    #os.mkdir(temp_env) 
    sp.check_output(["conda", "create", "--name", env_name])

    assert utils.prefix_in_conda(utils.conda_root()) ## conda_root, Test environment path
    assert utils.prefix_in_conda(os.path.basename(utils.conda_root())) ## conda_root, Test environment name

    assert utils.prefix_in_conda(temp_env) ## temp_env, Test environment path
    assert utils.prefix_in_conda(env_name) ## temp_env, test environment name

    environments = [os.path.join(x+"/") for x in utils.check_output(["conda", "info", "--env"]).strip().replace("*","").replace("\n"," ").split(" ") if os.path.isdir(x)]

    for env in environments:
        assert utils.prefix_in_conda(env) ## test environment path
        assert utils.prefix_in_conda(os.path.basename(env.rstrip("/"))) ## Test environment name (basename does not work if it is a directory. Must strip the trailing "/" if it exists

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


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


def test_get_file_md5sum():
    """
    Test the get_file_md5sum correctly gets a md5sum for the file path provided.
    """
    pytest_enable_socket()

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
    bed_files_path = bedfiles.recipe_dirs["bedfiles"]   
    
    ## bgzip and tabix cpg bed file
    for f in os.listdir(bed_files_path):
        sp.check_output("bgzip "+os.path.join(bed_files_path,f), shell=True)
        sp.check_output("tabix "+os.path.join(bed_files_path,f)+".gz", shell=True)

    ## Check the cpg bed file exists and is a file
    assert os.path.exists(os.path.join(bed_files_path,"cpg.bed.gz")) == True
    assert os.path.isfile(os.path.join(bed_files_path,"cpg.bed.gz")) == True
    assert os.path.exists(os.path.join(bed_files_path,"cpg.bed.gz.tbi")) == True
    assert os.path.isfile(os.path.join(bed_files_path,"cpg.bed.gz.tbi")) == True

    ## Check the md5sum method gets the same md5sum as the linux md5sum module
    for f in glob.glob(os.path.join(bed_files_path,"*")):
        file_name = os.path.basename(f)
        file_md5sum = utils.get_file_md5sum(f)

        ## md5_out = list: [0] = md5sum, [1] = file path
        linux_md5sum = str(re.sub(" +", "\t", sp.check_output(["md5sum", f]).decode("utf8"))).strip().split("\t")

        assert linux_md5sum[0] == file_md5sum


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
    vcf_files_path = vcffiles.recipe_dirs["vcffiles"]   
    for f in os.listdir(vcf_files_path):
        sp.check_output("bgzip "+os.path.join(vcf_files_path,f), shell=True)
        sp.check_output("tabix "+os.path.join(vcf_files_path,f+".gz"), shell=True)

    ## Check the vcf file exists and is a file
    assert os.path.exists(os.path.join(vcf_files_path,"some.vcf.gz")) == True
    assert os.path.isfile(os.path.join(vcf_files_path,"some.vcf.gz")) == True
    assert os.path.exists(os.path.join(vcf_files_path,"some.vcf.gz.tbi")) == True
    assert os.path.isfile(os.path.join(vcf_files_path,"some.vcf.gz.tbi")) == True

    ## Check the md5sum method gets the same md5sum as the linux md5sum module
    for f in glob.glob(os.path.join(vcf_files_path,"*")):
        file_name = os.path.basename(f)
        file_md5sum = utils.get_file_md5sum(f)

        ## md5_out = list: [0] = md5sum, [1] = file path
        linux_md5sum = str(re.sub(" +", "\t", sp.check_output(["md5sum", f]).decode("utf8"))).strip().split("\t")

        assert linux_md5sum[0] == file_md5sum


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
        test.fa.fai: |
            chr1\t249250621\t6\t50\t51  
            chr2\t243199373\t254235646\t50\t51  
            chr3\t198022430\t502299013\t50\t51  
            chr4\t191154276\t704281898\t50\t51  
            chr5\t180915260\t899259266\t50\t51  

    """, from_string=True)
    
    fastafile.write_recipes()
    fasta_files_path = fastafile.recipe_dirs["fastafile"]   

    ## Check the fasta file exists and is a file
    assert os.path.exists(os.path.join(fasta_files_path,"test.fa")) == True
    assert os.path.isfile(os.path.join(fasta_files_path,"test.fa")) == True
    assert os.path.exists(os.path.join(fasta_files_path,"test.fa.fai")) == True
    assert os.path.isfile(os.path.join(fasta_files_path,"test.fa.fai")) == True

    ## Check the md5sum method gets the same md5sum as the linux md5sum module
    for f in glob.glob(os.path.join(fasta_files_path,"*")):
        file_name = os.path.basename(f)
        file_md5sum = utils.get_file_md5sum(f)

        ## md5_out = list: [0] = md5sum, [1] = file path
        linux_md5sum = str(re.sub(" +", "\t", sp.check_output(["md5sum", f]).decode("utf8"))).strip().split("\t")

        assert linux_md5sum[0] == file_md5sum


def test_get_checksum_dict_from_txt():
        """
        Test that the get_checksum_dict_from_txt method correctly returns the file-md5sum paris correctly
        """
        pytest_enable_socket()

        recipe = CreateRecipe(
        """
        checksum_test:
            checksums_file.txt: |

            checksums_file2.txt: |
                file1\tflasdjoi32mljsdlj3i
                file2\tlaj2jo8sjfwiefm90sf

            checksums_file3.txt: |
                cpg.bed.gz\tef067178b98b928e16dfc4fb331f45a0
                cpg.bed.gz.tbi\t72131322ce5076a83c80e051ae5c4a7c

        """, from_string=True)

        recipe.write_recipes()

        recipe_dir_path = recipe.recipe_dirs["checksum_test"] 

        checksum1 = os.path.join(recipe_dir_path, "checksums_file.txt")
        checksum2 = os.path.join(recipe_dir_path, "checksums_file2.txt")
        checksum3 = os.path.join(recipe_dir_path, "checksums_file3.txt")

        ## Get checkusm file dict for checksum1
        checksum_dict1 = utils.get_checksum_dict_from_txt(checksum1)

        ## Check that the dict is empty
        assert not checksum_dict1 

        ## Get checkusm file dict for checksum2
        checksum_dict2 = utils.get_checksum_dict_from_txt(checksum2)

        ## Check that the file and md5sum values were correctly gathered 
        for key, value in checksum_dict2.items():
            assert (key == "file1" and value == "flasdjoi32mljsdlj3i") or (key == "file2" and value == "laj2jo8sjfwiefm90sf") 

        ## Get checkusm file dict for checksum3
        checksum_dict3 = utils.get_checksum_dict_from_txt(checksum3)

        ## Check that the file and md5sum values were correctly gathered 
        for key, value in checksum_dict3.items():
            assert (key == "cpg.bed.gz" and value == "ef067178b98b928e16dfc4fb331f45a0") or (key == "cpg.bed.gz.tbi" and value == "72131322ce5076a83c80e051ae5c4a7c")


def test_get_checksum_dict_from_tar():
    """
    test that the get_checksum_dict_from_tar correctly returns the checksum file md5sums from a tar.bz2 file
    """
    pytest_enable_socket()

    recipe = CreateRecipe(
    """
    trial-recipe-v1:
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
              name: trial-recipe-v1
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
                genomic-coordinate-base: 0-based-inclusive
                data-version: 11-Mar-2019
                data-provider: UCSC
                file-type: 
                - bed
                final-files: 
                - trial-recipe-v1.bed.gz
                - trial-recipe-v1.bed.gz.tbi
                ggd-channel: genomics
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset

            genome=https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg38/hg38.genome
            wget --quiet -O - http://hgdownload.cse.ucsc.edu/goldenpath/hg38/database/gap.txt.gz \\
            | gzip -dc \\
            | awk -v OFS="\t" 'BEGIN {print "#chrom\tstart\tend\tsize\ttype\tstrand"} {print $2,$3,$4,$7,$8,"+"}' \\
            | gsort /dev/stdin $genome \\
            | bgzip -c > trail-recipe-v1.bed.gz

            tabix trail-recipe-v1.bed.gz 
        
        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-ucsc-v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-ucsc-v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg38/trial-hg38-gaps-ucsc-v1/1
            fi

            PKG_DIR=`find "$CONDA_SOURCE_PREFIX/pkgs/" -name "$PKG_NAME-$PKG_VERSION*" | grep -v ".tar.bz2" |  grep "$PKG_VERSION.*$PKG_BUILDNUM$"`

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
                (mv $f "trial-hg38-gaps-ucsc-v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_trial-hg38-gaps-ucsc-v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_trial-hg38-gaps-ucsc-v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_trial-hg38-gaps-ucsc-v1_dir"
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

        checksums_file.txt: |
            trial-recipe-v1.bed.gz\t7f15bfe96b36a261fa36ae6d5a68b977
            trial-recipe-v1.bed.gz.tbi\t41ef3698f44adc8f0c7b0f0e1fef6637

    """, from_string=True)

    recipe.write_recipes()

    from ggd import check_recipe

    ## build tar.bz2 file
    recipe_dir_path = recipe.recipe_dirs["trial-recipe-v1"] 
    yaml_file = yaml.safe_load(open(os.path.join(recipe_dir_path, "meta.yaml")))
    tarball_file_path = check_recipe._build(recipe_dir_path,yaml_file)

    assert os.path.isfile(tarball_file_path)
    assert "noarch" in tarball_file_path

    checksum_dict = utils.get_checksum_dict_from_tar(tarball_file_path)

    for key,value in checksum_dict.items():
        assert (key == "trial-recipe-v1.bed.gz" and value == "7f15bfe96b36a261fa36ae6d5a68b977") or \
                (key == "trial-recipe-v1.bed.gz.tbi" and value == "41ef3698f44adc8f0c7b0f0e1fef6637")


def test_data_file_checksum():
    """
    Test the data_file_checksum method works correctly. This is the main method to compare the recipe checksum with 
     the installed file's md5sum checksum
    """
    
    pytest_enable_socket()

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
    bed_files_path = bedfiles.recipe_dirs["bedfiles"]   

    ## bgzip and tabix cpg bed file
    for f in os.listdir(bed_files_path):
        sp.check_output("bgzip "+os.path.join(bed_files_path,f), shell=True)
        sp.check_output("tabix "+os.path.join(bed_files_path,f)+".gz", shell=True)

    ## Check the cpg bed file exists and is a file
    assert os.path.exists(os.path.join(bed_files_path,"cpg.bed.gz")) == True
    assert os.path.isfile(os.path.join(bed_files_path,"cpg.bed.gz")) == True
    assert os.path.exists(os.path.join(bed_files_path,"cpg.bed.gz.tbi")) == True
    assert os.path.isfile(os.path.join(bed_files_path,"cpg.bed.gz.tbi")) == True


    ## Test good checkusm
    ### create checksum file
    cpg_bed_gz_md5sum = file_md5sum = utils.get_file_md5sum(os.path.join(bed_files_path,"cpg.bed.gz"))
    cpg_bed_gz_tbi_md5sum = file_md5sum = utils.get_file_md5sum(os.path.join(bed_files_path,"cpg.bed.gz.tbi"))

    bed_checksum = CreateRecipe(
    """
    bed_checksum:
        checksums_file.txt: |
            cpg.bed.gz\t{gz}
            cpg.bed.gz.tbi\t{tbi}
    """.format(gz=cpg_bed_gz_md5sum, tbi=cpg_bed_gz_tbi_md5sum), from_string=True)

    bed_checksum.write_recipes()

    bed_checksum_path = bed_checksum.recipe_dirs["bed_checksum"]

    checksum_dict = utils.get_checksum_dict_from_txt(os.path.join(bed_checksum_path,"checksums_file.txt"))

    ## Test good run without errors
    assert utils.data_file_checksum(bed_files_path,checksum_dict) == True


    ## Test unequal number of files
    bed_checksum2 = CreateRecipe(
    """
    bed_checksum2:
        checksums_file.txt: |
            cpg.bed.gz\t{gz}
    """.format(gz=cpg_bed_gz_md5sum), from_string=True)

    bed_checksum2.write_recipes()

    bed_checksum2_path = bed_checksum2.recipe_dirs["bed_checksum2"]

    checksum_dict2 = utils.get_checksum_dict_from_txt(os.path.join(bed_checksum2_path,"checksums_file.txt"))

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        utils.data_file_checksum(bed_files_path,checksum_dict2)
    output = temp_stdout.getvalue().strip() 
    assert ("!!ERROR!!: The number of installed files does not match the number of checksum files" in output)


    ## Test bad md5sums
    bed_checksum3 = CreateRecipe(
    """
    bed_checksum3:
        checksums_file.txt: |
            cpg.bed.gz\to3sljala3lkjad3ljasjlaslf
            cpg.bed.gz.tbi\ta2lajsfoijasliejalias
    """, from_string=True)

    bed_checksum3.write_recipes()

    bed_checksum3_path = bed_checksum3.recipe_dirs["bed_checksum3"]

    checksum_dict3 = utils.get_checksum_dict_from_txt(os.path.join(bed_checksum3_path,"checksums_file.txt"))
    print(checksum_dict3)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        utils.data_file_checksum(bed_files_path,checksum_dict3)
    output = temp_stdout.getvalue().strip() 
    assert ("!!ERROR!!: The {f} file's checksums don't match, suggesting that the file wasn't installed properly".format(f = "cpg.bed.gz") in output) or \
           ("!!ERROR!!: The {f} file's checksums don't match, suggesting that the file wasn't installed properly".format(f = "cpg.bed.gz.tbi") in output)


    ## Test differint names within checksum_file and installed files
    bed_checksum4 = CreateRecipe(
    """
    bed_checksum4:
        checksums_file.txt: |
            bad_name.bed.gz\t{gz}
            bad_name.gz.tbi\t{tbi}
    """.format(gz=cpg_bed_gz_md5sum, tbi=cpg_bed_gz_tbi_md5sum), from_string=True)

    bed_checksum4.write_recipes()

    bed_checksum4_path = bed_checksum4.recipe_dirs["bed_checksum4"]

    checksum_dict4 = utils.get_checksum_dict_from_txt(os.path.join(bed_checksum4_path,"checksums_file.txt"))

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        utils.data_file_checksum(bed_files_path,checksum_dict4)
    output = temp_stdout.getvalue().strip() 
    assert ("!!ERROR!!: The installed file {f} is not one of the checksum files".format(f = "cpg.bed.gz") in output) or ("!!ERROR!!: The installed file {f} is not one of the checksum files".format(f = "cpg.bed.gz.tbi") in output)


def test_bypass_satsolver_on_install():
    """
    Test that the bypass_satsolver_on_install function properly installs a cached packages and bypasses sat solving
    """
    pytest_enable_socket()

    ## Test a bad install, bad recipe
    ggd_package = "Bad-package"
    ggd_channel = "ggd-genomics"

    try:
        utils.bypass_satsolver_on_install([ggd_package],conda_channel = ggd_channel)
        assert False
    except:
        pass


    ## Test a bad install, bad channel
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "ggd-not-a-ggd-channel"

    try:
        utils.bypass_satsolver_on_install([ggd_package],conda_channel = ggd_channel)
        assert False
    except:
        pass

    ## Test a bad install, non list recipe input
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

    assert utils.bypass_satsolver_on_install([ggd_package],conda_channel = ggd_channel) == True



