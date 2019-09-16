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
import shutil
from copy import deepcopy
from argparse import Namespace
from argparse import ArgumentParser
import glob
import contextlib
import tarfile
import glob
from helpers import install_hg19_gaps_ucsc_v1, uninstall_hg19_gaps_ucsc_v1
from ggd import install 
from ggd import utils
from ggd import uninstall
from ggd.utils import CondaEnvironmentNotFound 
from ggd.utils import get_conda_package_list

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
TEST_LABEL = "ggd-install-test"


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


#---------------------------------------------------------------------------------------------------------
## Unit Tests for ggd install
#---------------------------------------------------------------------------------------------------------


def remove_pfam():
    """
    Helper script to setup install run
    """

    ## Uninstall pfam for later use
    ggd_recipe = "hg19-pfam-domains-ucsc-v1"
    if ggd_recipe not in str(sp.check_output(["conda", "list"]).decode('utf8')):
        try:
            uninstall.uninstall((),Namespace(channel='genomics', command='uninstall', name=ggd_recipe))
            sp.check_output(["conda", "uninstall", ggd_recipe]) 
        except:
            pass


def test_check_ggd_recipe_fake_recipe():
    """
    Test the check_ggd_recipe function returns None if an invalide recipe is provided
    """
    pytest_enable_socket()
    remove_pfam()

    assert install.check_ggd_recipe("Not_a_real_recipe","genomics") == None


def test_check_ggd_recipe_fake_channel():
    """
    Test the check_ggd_recipe function exits if an invalide ggd channel is provided
    """
    pytest_enable_socket()

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_ggd_recipe("hg19-gaps","ggd-fake-channel")
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("The 'ggd-fake-channel' channel is not a ggd conda channel") ## Check that the exit code is 1


def test_check_ggd_recipe_good_run():
    """
    Test the check_ggd_recipe function returns a dict with information from the recipe
    """
    pytest_enable_socket()

    tmp_recipe = "hg19-gaps-ucsc-v1"

    jdict = install.check_ggd_recipe(tmp_recipe,"genomics")
    assert type(jdict) == type(dict())
    assert jdict["packages"][tmp_recipe] 
    assert jdict["packages"][tmp_recipe]["identifiers"]["species"] == "Homo_sapiens"
    assert jdict["packages"][tmp_recipe]["identifiers"]["genome-build"] == "hg19"
    

def test_check_if_installed_recipe_not_installed():
    """
    Test if the check_if_installed function correclty identifies that the ggd data package is not installed.
    """
    pytest_enable_socket()

    recipe = "Fake_hg19-gaps"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                    {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', 
                    u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                    {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                    u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'hg19', u'species': u'Homo_sapiens'}}}}
    default_version = -1
    
    assert install.check_if_installed(recipe,ggd_jdict,default_version) == False


def test_check_if_installed_recipe_is_installed():
    """
    Test if the check_if_installed function correclty identifies that the ggd data package is installed.
    """
    pytest_enable_socket()


    recipe = "hg19-gaps-ucsc-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-ucsc-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/hg19-gaps-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                    u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'hg19', u'species': u'Homo_sapiens'}}}}
    default_version = "-1"

    species = ggd_jdict["packages"][recipe]["identifiers"]["species"]
    build = ggd_jdict["packages"][recipe]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][recipe]["version"]
    
    CONDA_ROOT = utils.conda_root()

    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,recipe,version)

    path_added = False
    if not glob.glob(path):
        os.makedirs(path)
        path_added = True
   
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_if_installed(recipe,ggd_jdict,default_version)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    if path_added:
       os.rmdir(path) ## Remove the bottom directory from the path if it was created. 
    

def test_check_if_installed_recipe_v9999_is_not_installed():
    """
    Test if the check_if_installed function correclty identifies that the ggd data package is installed but not the sepcific version.
    """
    pytest_enable_socket()

    recipe = "hg19-gaps-ucsc-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-ucsc-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/hg19-gaps-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                    u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'hg19', u'species': u'Homo_sapiens'}}}}
    default_version = "9999"

    species = ggd_jdict["packages"][recipe]["identifiers"]["species"]
    build = ggd_jdict["packages"][recipe]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][recipe]["version"]
    
    CONDA_ROOT = utils.conda_root()

    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,recipe,version)

    path_added = False
    if not glob.glob(path):
        os.makedirs(path)
        path_added = True
   
    assert install.check_if_installed(recipe,ggd_jdict,default_version) == False

    if path_added:
       os.rmdir(path) ## Remove the bottom directory from the path if it was created. 


def test_check_if_installed_with_prefix_set():
    """
    Test that the ggd can identify in a data package has been installed in a different (targeted) conda environemnt 
    """
    pytest_enable_socket()

    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "temp_env"])


    ## Check that an uninstalled data package is correclty stated as such
    recipe = "Fake_hg19-gaps"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                    {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', 
                    u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                    {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                    u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'hg19', u'species': u'Homo_sapiens'}}}}
    default_version = -1
    
    assert install.check_if_installed(recipe,ggd_jdict,default_version,prefix=temp_env) == False

    ## Check that an installed data package is stated as such
    ggd_package = "hg19-pfam-domains-ucsc-v1"
    sp.check_output(["ggd", "install", "--prefix", temp_env, ggd_package])

    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-pfam-domains-ucsc-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/hg19-pfam-domains-ucsc-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains',u'protein',u'protein-domains',u'UCSC',u'bed',u'bed-file'], 
                    u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, 
                    u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}}

    default_version = "-1"

    species = ggd_jdict["packages"][ggd_package]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_package]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_package]["version"]
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_if_installed(ggd_package,ggd_jdict,default_version, prefix=temp_env)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    file1 = "{}.bed12.bed.gz".format(ggd_package)
    file2 = "{}.bed12.bed.gz.tbi".format(ggd_package)
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file1))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file2))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,ggd_package,version,file1)) == False
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,ggd_package,version,file2)) == False

    ## Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False
    
   
def test_check_conda_installation_pacakge_no_installed():
    """
    Test check conda instllation function correclty identifies that a data pacakges is not installed by conda
    """
    pytest_enable_socket()

    recipe = "Fake-hg19-gaps"
    version = "1"

    assert install.check_conda_installation(recipe,version) == False


def test_check_conda_installation_pacakge_no_installed_no_version_designation():
    """
    Test check conda instllation function correclty identifies that a data pacakges is not installed by conda
    """
    pytest_enable_socket()

    recipe = "Fake-hg19-gaps"
    version = "-1"

    assert install.check_conda_installation(recipe,version) == False


def test_check_conda_installation_pacakge_is_installed():
    """
    Test check conda instllation function correclty identifies that a data pacakges has been installed by conda.
     This method calls the install_hg19_gaps  to run.
    """
    pytest_enable_socket()

    ## Install hg19-gaps-ucsc-v1
    recipe = "hg19-gaps-ucsc-v1"
    args = Namespace(channel='genomics', command='install', debug=False, name=recipe, version='-1', prefix=None)
    try:
        install.install((), args)
    except SystemExit:
        pass
    jdict = install.check_ggd_recipe(recipe,"genomics")
    version = jdict["packages"][recipe]["version"]
    

    ## Test that it is already installed
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_conda_installation(recipe,version)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    try:
        uninstall_hg19_gaps_ucsc_v1()
    except:
        pass


def test_check_conda_installation_pacakge_is_installed_noninstalled_version_desingation():
    """
    Test check conda instllation function correclty identifies that a data pacakges has been installed by conda.
     but that it has not installed the specied version
    """
    pytest_enable_socket()

    recipe = "hg19-gaps-ucsc-v1"
    version = "9999"

    assert install.check_conda_installation(recipe,version) == False


def test_check_conda_installation_pacakge_is_installed_no_version_designation():
    """
    Test check conda instllation function correclty identifies that a data pacakges has been installed by conda.
     The version will be set to -1, meaning the version is not specified
    """
    pytest_enable_socket()

    try:
     install_hg19_gaps_ucsc_v1()
    except:
        pass

    recipe = "hg19-gaps-ucsc-v1"
    version = "-1"

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_conda_installation(recipe,version)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    try:
        uninstall_hg19_gaps_ucsc_v1()
    except:
        pass


def test_check_conda_installation_pacakge_no_installed_longer_package_name():
    """
    Test check conda instllation function correclty identifies that a data pacakges is not installed by conda
    """
    pytest_enable_socket()

    recipe = "hg19-gapsss-ucsc-v1"
    version = "-1"

    assert install.check_conda_installation(recipe,version) == False


def test_check_conda_installation_pacakge_no_installed_shorter_package_name():
    """
    Test check conda instllation function correclty identifies that a data pacakges is not installed by conda
    """
    pytest_enable_socket()

    recipe = "hg19-ga"
    version = "-1"

    assert install.check_conda_installation(recipe,version) == False


def test_check_conda_installed_with_prefix_set():
    """
    Test that an installed data package designated by the prfeix flag can be detected by conda 
    """
    pytest_enable_socket()

    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env2")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env2"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "temp_env2"])

    ## Check that an uninstalled package in a specific prefix is properly identified
    ggd_package = "hg19-pfam-domains-ucsc-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-pfam-domains-ucsc-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/hg19-pfam-domains-ucsc-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains',u'protein',u'protein-domains',u'UCSC',u'bed',u'bed-file'], 
                    u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, 
                    u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}}

    default_version = "-1"

    assert install.check_conda_installation(ggd_package,default_version,prefix=temp_env) == False


    ## Check that an installed data package is stated as such
    sp.check_output(["ggd", "install", "--prefix", temp_env, ggd_package])

    species = ggd_jdict["packages"][ggd_package]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_package]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_package]["version"]
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_conda_installation(ggd_package,default_version,prefix=temp_env) 
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    file1 = "{}.bed12.bed.gz".format(ggd_package)
    file2 = "{}.bed12.bed.gz.tbi".format(ggd_package)
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file1))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file2))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,ggd_package,version,file1)) == False
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,ggd_package,version,file2)) == False

    ## Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env2"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


def test_check_S3_bucket_not_uploaded():
    """
    Test if a recipe is cached on s3 or not. 
    """     
    pytest_enable_socket()

    recipe = "hg19-gaps-ucsc-v1"

    ## If no tags key avaible return false
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-ucsc-v1': {u'activate.d': 
                    False, u'version': u'1', u'post_link': True, u'binary_prefix': False, u'run_exports': {}, 
                    u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/hg19-gaps-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                    u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'hg19', u'species': u'Homo_sapiens'}}}}

    assert install.check_S3_bucket(recipe, ggd_jdict) == False

    ## If not cached key in tags return false 
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-ucsc-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, 
                    u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': 
                    [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-v1-1-1.tar.bz2', 
                    u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', 
                    u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': 
                    u'Homo_sapiens'}}}}

    assert install.check_S3_bucket(recipe, ggd_jdict) == False

    ## If no "uploaded_to_aws" Signature in cached return false
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-ucsc-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/hg19-gaps-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                    u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'hg19', u'species': u'Homo_sapiens'}}}}

    assert install.check_S3_bucket(recipe, ggd_jdict) == False


def test_check_S3_bucket_is_uploaded():
    """
    Test if a recipe is cached on s3 not. 
    """     
    pytest_enable_socket()

    recipe = "hg19-gaps-ucsc-v1"
    ## Return True if uploaded to aws
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-ucsc-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', 
                    u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                    {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/hg19-gaps-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                    u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'hg19', u'species': u'Homo_sapiens'}}}}

    assert install.check_S3_bucket(recipe, ggd_jdict) == True


def test_install_from_cache():
    """
    Test install from cache function for proper installation from cached recipe
    """
    pytest_enable_socket()

    ## Bad install
    name = "Fake_hg19-gaps"
    ggd_channel = "genomics"
    default_version = -1
    jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                {u'activate.d': False, u'version': u'1', u'tags': {u'cached': ["uploaded_to_aws"], u'ggd-channel': u'genomics', 
                u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                u'hg19', u'species': u'Homo_sapiens'}}}}
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install_from_cached(name, ggd_channel,jdict,default_version)   
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    ## Good Install 
    name = "hg19-cpg-islands-ucsc-v1"
    ggd_channel = "genomics"
    default_version = "-1" 

    jdict = install.check_ggd_recipe(name,ggd_channel)

    assert install.install_from_cached(name, ggd_channel,jdict,default_version) == True   

    ### Test that the ggd_info metadata is updated with ggd pkg
    pkg_info = get_conda_package_list(utils.conda_root(),name)
    assert name in pkg_info.keys()
    version = pkg_info[name]["version"]
    build = pkg_info[name]["build"]
    assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","noarch"))
    assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","noarch",name+"-{}-{}.tar.bz2".format(version,build)))
    assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","channeldata.json"))
    with open(os.path.join(utils.conda_root(),"share","ggd_info","channeldata.json")) as jfile:
        channeldata = json.load(jfile)
        assert name in channeldata["packages"]

    try:
        args = Namespace(channel='genomics', command='uninstall', name=name)
        uninstall.uninstall((),args)
    except:
        pass


def test_install_from_cache_with_prefix_set():
    """
    Test install from cache function for proper installation from cached recipe
    """
    pytest_enable_socket()

    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env3")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env3"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "temp_env3"])

    ## Bad install
    name = "Fake_hg19-gaps"
    ggd_channel = "genomics"
    default_version = -1
    jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                {u'activate.d': False, u'version': u'1', u'tags': {u'cached': ["uploaded_to_aws"], u'ggd-channel': u'genomics', 
                u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                u'hg19', u'species': u'Homo_sapiens'}}}}
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install_from_cached(name, ggd_channel,jdict,default_version,prefix=temp_env)   
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 


    ## Good install 
    name = "hg19-pfam-domains-ucsc-v1"
    ggd_channel = "genomics"
    default_version = "-1"
    jdict = install.check_ggd_recipe(name,ggd_channel)

    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()

    assert install.install_from_cached(name, ggd_channel,jdict,default_version,prefix=temp_env) == True   

    species = jdict["packages"][name]["identifiers"]["species"]
    build = jdict["packages"][name]["identifiers"]["genome-build"]
    version = jdict["packages"][name]["version"]

    file1 = "{}.bed12.bed.gz".format(name)
    file2 = "{}.bed12.bed.gz.tbi".format(name)
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,name,version))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,file1))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,file2))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file1)) == False
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file2)) == False

    ## Test that the tarfile and the pkg dir were correctly copied to the prefix
    data_packages = get_conda_package_list(temp_env)
    version = str(data_packages[name]["version"])
    build_number = str(data_packages[name]["build"])
    tarfile = "{}-{}-{}.tar.bz2".format(name,version,build_number)
    pkgdir = "{}-{}-{}".format(name,version,build_number)

    assert os.path.isfile(os.path.join(temp_env,"pkgs",tarfile))
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir))

    ### Test that the ggd_info metadata is updated with ggd pkg
    pkg_info = get_conda_package_list(temp_env,name)
    assert name in pkg_info.keys()
    version = pkg_info[name]["version"]
    build = pkg_info[name]["build"]
    assert os.path.exists(os.path.join(temp_env,"share","ggd_info","noarch"))
    assert os.path.exists(os.path.join(temp_env,"share","ggd_info","noarch",name+"-{}-{}.tar.bz2".format(version,build)))
    assert os.path.exists(os.path.join(temp_env,"share","ggd_info","channeldata.json"))
    with open(os.path.join(temp_env,"share","ggd_info","channeldata.json")) as jfile:
        channeldata = json.load(jfile)
        assert name in channeldata["packages"]

    ## Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env3"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


def test_conda_install_bad_recipe():
    """
    Test that the conda_install function properly handels a bad recipe
    """
    pytest_enable_socket()


    ## Test with undesignated version
    name = "Fake_hg19-gaps"
    ggd_channel = "genomics"
    default_version = -1
    jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                {u'activate.d': False, u'version': u'1', u'tags': {u'cached': ["uploaded_to_aws"], u'ggd-channel': u'genomics', 
                u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                u'hg19', u'species': u'Homo_sapiens'}}}}

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.conda_install(name, ggd_channel,jdict,default_version)    
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 


    ## Test with designated version
    name = "Fake_hg19-gaps"
    ggd_channel = "genomics"
    default_version = 2
    jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                {u'activate.d': False, u'version': u'2', u'tags': {u'cached': ["uploaded_to_aws"], u'ggd-channel': u'genomics', 
                u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                u'hg19', u'species': u'Homo_sapiens'}}}}

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.conda_install(name, ggd_channel,jdict,default_version)    
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 


def test_conda_install():
    """
    Test conda install function for proper installation of a ggd recipe using conda
    """
    pytest_enable_socket()

    try:
        uninstall_hg19_gaps_ucsc_v1()
    except:
        pass

    name = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"

    ## Test with undesignated version
    default_version = "-1" 

    jdict = install.check_ggd_recipe(name,ggd_channel)

    species = jdict["packages"][name]["identifiers"]["species"]
    build = jdict["packages"][name]["identifiers"]["genome-build"]
    version = jdict["packages"][name]["version"]

    assert install.conda_install(name, ggd_channel,jdict,default_version) == True   

    ### Test that the file is in the correct prefix (the current conda root)
    file1 = "{}.bed.gz".format(name)
    file2 = "{}.bed.gz.tbi".format(name)
    assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file1))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file2))


    ### Test that the ggd_info metadata is updated with ggd pkg
    pkg_info = get_conda_package_list(utils.conda_root(),name)
    assert name in pkg_info.keys()
    version = pkg_info[name]["version"]
    build = pkg_info[name]["build"]
    assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","noarch"))
    assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","noarch",name+"-{}-{}.tar.bz2".format(version,build)))
    assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","channeldata.json"))
    with open(os.path.join(utils.conda_root(),"share","ggd_info","channeldata.json")) as jfile:
        channeldata = json.load(jfile)
        assert name in channeldata["packages"]

    uninstall_hg19_gaps_ucsc_v1()

    ## Test with designated version
    default_version = "1" 

    assert install.conda_install(name, ggd_channel,jdict,default_version) == True   


def test_conda_install_with_prefix_set():
    """
    Test conda install function for proper installation of a ggd recipe using conda
    """
    pytest_enable_socket()

    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env4")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env4"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "temp_env4"])

    name = "hg19-pfam-domains-ucsc-v1"
    ggd_channel = "genomics"
    default_version = "-1"
    jdict = install.check_ggd_recipe(name,ggd_channel)

    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()

    assert install.conda_install(name, ggd_channel,jdict,default_version,prefix=temp_env) == True   

    species = jdict["packages"][name]["identifiers"]["species"]
    build = jdict["packages"][name]["identifiers"]["genome-build"]
    version = jdict["packages"][name]["version"]

    file1 = "{}.bed12.bed.gz".format(name)
    file2 = "{}.bed12.bed.gz.tbi".format(name)
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,name,version))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,file1))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,file2))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file1)) == False
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file2)) == False

    ## Test that the tarfile and the pkg dir were correctly copied to the prefix
    data_packages = get_conda_package_list(temp_env)
    version = str(data_packages[name]["version"])
    build_number = str(data_packages[name]["build"])
    tarfile = "{}-{}-{}.tar.bz2".format(name,version,build_number)
    pkgdir = "{}-{}-{}".format(name,version,build_number)

    assert os.path.isfile(os.path.join(temp_env,"pkgs",tarfile))
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir))

    ### Test that the ggd_info metadata is updated with ggd pkg
    pkg_info = get_conda_package_list(temp_env,name)
    assert name in pkg_info.keys()
    version = pkg_info[name]["version"]
    build = pkg_info[name]["build"]
    assert os.path.exists(os.path.join(temp_env,"share","ggd_info","noarch"))
    assert os.path.exists(os.path.join(temp_env,"share","ggd_info","noarch",name+"-{}-{}.tar.bz2".format(version,build)))
    assert os.path.exists(os.path.join(temp_env,"share","ggd_info","channeldata.json"))
    with open(os.path.join(temp_env,"share","ggd_info","channeldata.json")) as jfile:
        channeldata = json.load(jfile)
        assert name in channeldata["packages"]

    ## Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env4"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


def test_get_file_location():
    """
    Test that get_file_location function to properly reterive the location of the ggd file
    """
    pytest_enable_socket()

    ## Fake recipe
    ggd_recipe = "Fake_hg19-gaps"
    ggd_channel = "genomics"
    default_version = -1
    jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                {u'activate.d': False, u'version': u'1', u'tags': {u'cached': ["uploaded_to_aws"], u'ggd-channel': u'genomics', 
                u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                u'hg19', u'species': u'Homo_sapiens'}}}}
    
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]
    CONDA_ROOT = utils.conda_root()
    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        install.get_file_locations(ggd_recipe,jdict,default_version)
    output = temp_stdout.getvalue().strip() 
    assert "Installation complete. The downloaded data files are located at:" in output
    assert path in output
    assert "A new environment variable that points to data package directory path has been created:" in output
    assert "$ggd_{}_dir".format(ggd_recipe.replace("-","_")) in output
    assert "$ggd_{}_file".format(ggd_recipe.replace("-","_")) not in output


    ## The installed hg19-gaps-v1 recipe
    ggd_recipe = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    default_version = "-1" 

    jdict = install.check_ggd_recipe(ggd_recipe,ggd_channel)
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]
    CONDA_ROOT = utils.conda_root()
    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        install.get_file_locations(ggd_recipe,jdict,default_version)
    output = temp_stdout.getvalue().strip() 
    assert "Installation complete. The downloaded data files are located at:" in output
    assert path in output
    assert "A new environment variable that points to data package directory path has been created:" in output
    assert "$ggd_{}_dir".format(ggd_recipe.replace("-","_")) in output
    assert "A new environment variable that points to the installed file has been created:" in output
    assert "$ggd_{}_file".format(ggd_recipe.replace("-","_")) in output


def test_get_file_location_with_prefix_set():
    """
    Test that get_file_location function to properly reterive the location of the ggd file when it is associated with a different prefix (conda environment)
    """
    pytest_enable_socket()

    ### Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env5")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env5"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "temp_env5"])

    ### Install the recipe
    ggd_recipe = "hg19-pfam-domains-ucsc-v1"
    ggd_channel = "genomics"
    default_version = "-1"

    jdict = install.check_ggd_recipe(ggd_recipe,ggd_channel)
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]

    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()
    assert install.install_from_cached(ggd_recipe, ggd_channel,jdict,default_version,prefix=temp_env) == True   

    path = os.path.join(temp_env,"share","ggd",species,build,ggd_recipe,version)

    ### Test output from get file location
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        install.get_file_locations(ggd_recipe,jdict,default_version,prefix=temp_env)
    output = temp_stdout.getvalue().strip() 
    assert "Installation complete. The downloaded data files are located at:" in output
    assert path in output
    assert "A new environment variable that points to data package directory path has been created:" in output
    assert "-> NOTE: These environment variables are specific to the {p} conda environment and can only be accessed from within that environmnet".format(p=temp_env) in output
    assert "$ggd_{}_dir".format(ggd_recipe.replace("-","_")) in output
    assert "A new environment variable that points to the installed file has been created:" in output
    assert "$ggd_{}_file".format(ggd_recipe.replace("-","_")) in output

    ### Test the file exists in the correct prefix and not the current prefix
    file1 = "{}.bed12.bed.gz".format(ggd_recipe)
    file2 = "{}.bed12.bed.gz.tbi".format(ggd_recipe)
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_recipe,version))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,ggd_recipe,version,file1))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,ggd_recipe,version,file2))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,ggd_recipe,version,file1)) == False
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,ggd_recipe,version,file2)) == False

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env5"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


def test_copy_pkg_files_to_prefix():
    """
    Test that the copy_pkg_files_to_prefix method correctly copies the tarball and pkg files from the current 
     conda environment to the target prefix
    """
    pytest_enable_socket()

    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env6")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env6"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass

    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "temp_env6"])

    ### Install the recipe
    ggd_recipe = "hg19-pfam-domains-ucsc-v1"
    ggd_channel = "genomics"
    default_version = "-1"
    jdict = install.check_ggd_recipe(ggd_recipe,ggd_channel)

    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()
    assert install.install_from_cached(ggd_recipe, ggd_channel,jdict,default_version,prefix=temp_env) == True   

    ## Test a prefix that is the same and the conda root returns False
    assert install.copy_pkg_files_to_prefix(utils.conda_root(),ggd_recipe) == False

    ## Extra info
    data_packages = get_conda_package_list(temp_env)
    version = str(data_packages[ggd_recipe]["version"])
    build = str(data_packages[ggd_recipe]["build"])

    ## Test that the files were properly copied
    tarfile = "{}-{}-{}.tar.bz2".format(ggd_recipe,version,build)
    pkgdir = "{}-{}-{}".format(ggd_recipe,version,build)
    assert  os.path.isfile(os.path.join(temp_env,"pkgs",tarfile)) == True
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir)) == True

    ## Remove them from the target prefix
    os.remove(os.path.join(temp_env,"pkgs",tarfile))
    shutil.rmtree(os.path.join(temp_env,"pkgs",pkgdir))
    assert  os.path.isfile(os.path.join(temp_env,"pkgs",tarfile)) == False
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir)) == False

    ### Test the function passes
    assert install.copy_pkg_files_to_prefix(temp_env,ggd_recipe) == True

    ### Test the files are correct
    assert  os.path.isfile(os.path.join(utils.conda_root(),"pkgs",tarfile))
    assert os.path.isdir(os.path.join(utils.conda_root(),"pkgs",pkgdir))
    assert  os.path.isfile(os.path.join(temp_env,"pkgs",tarfile))
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir))
    
    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env6"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False
    

def test_install_main_function():
    """
    Test the main install function
    """
    pytest_enable_socket()

    remove_pfam()

    CONDA_ROOT = utils.conda_root()

    ## Test a non ggd recipe
    ggd_recipe1 = "Fake-hg19-gaps"
    args = Namespace(channel='genomics', command='install', debug=False, name=ggd_recipe1, version='-1',prefix=None)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    ## Install pfam
    ggd_recipe = "hg19-pfam-domains-ucsc-v1"
    args = Namespace(channel='genomics', command='install', debug=False, name=ggd_recipe, version='-1',prefix=None)
    assert install.install((), args) == True

    ## Test an already installed ggd recipe
    args = Namespace(channel='genomics', command='install', debug=False, name=ggd_recipe, version='-1',prefix=None)
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    ## Test a previously installed recipe, but the recipe path is broken 
    ggd_recipe = "hg19-pfam-domains-ucsc-v1"
    args = Namespace(channel='genomics', command='install', debug=False, name=ggd_recipe, version='-1',prefix=None)

    jdict = install.check_ggd_recipe(ggd_recipe,"genomics")
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]

    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)
    for f in os.listdir(path):
        os.remove(os.path.join(path,f))
    os.rmdir(path)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    remove_pfam()


def test_install_main_function_with_prefix_set():
    """
    Test the main install function with the prefix flag set
    """
    pytest_enable_socket()

    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env7")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env7"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass

    ggd_recipe = "hg19-pfam-domains-ucsc-v1"
    ggd_channel="genomics"
    args = Namespace(channel='genomics', command='install', debug=False, name=ggd_recipe, version='-1', prefix = temp_env)

    ## Test that an environemnt that doesn't exist is probably handeld
    try:
        install.install((), args)
        ## If it passes then there is an error
        assert False
    except CondaEnvironmentNotFound as e:
        pass
    except Exception as e:
        assert False

    ## Test a good install into a designated prefix
    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "temp_env7"])

    jdict = install.check_ggd_recipe(ggd_recipe,ggd_channel)
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]

    assert install.install((), args) == True

    ### Test the file exists in the correct prefix and not the current prefix
    file1 = "{}.bed12.bed.gz".format(ggd_recipe)
    file2 = "{}.bed12.bed.gz.tbi".format(ggd_recipe)
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_recipe,version))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,ggd_recipe,version,file1))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,ggd_recipe,version,file2))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,ggd_recipe,version,file1)) == False
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,ggd_recipe,version,file2)) == False

    assert "CONDA_SOURCE_PREFIX" in os.environ

    ## Test that the tarfile and the pkg dir were correctly copied to the prefix
    data_packages = get_conda_package_list(temp_env)
    version = str(data_packages[ggd_recipe]["version"])
    build_number = str(data_packages[ggd_recipe]["build"])
    tarfile = "{}-{}-{}.tar.bz2".format(ggd_recipe,version,build_number)
    pkgdir = "{}-{}-{}".format(ggd_recipe,version,build_number)

    assert os.path.isfile(os.path.join(temp_env,"pkgs",tarfile))
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir))

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env7"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False



