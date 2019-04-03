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
import glob
from helpers import install_hg19_gaps_v1, uninstall_hg19_gaps_v1
from ggd import install 
from ggd import utils
from ggd import uninstall

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO

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

def test_check_ggd_recipe_fake_recipe():
    """
    Test the check_ggd_recipe function returns None if an invalide recipe is provided
    """
    assert install.check_ggd_recipe("Not_a_real_recipe","genomics") == None


def test_check_ggd_recipe_fake_channel():
    """
    Test the check_ggd_recipe function exits if an invalide ggd channel is provided
    """
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_ggd_recipe("hg19-gaps","ggd-fake-channel")
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1

#
def test_check_ggd_recipe_good_run():
    """
    Test the check_ggd_recipe function returns a dict with information from the recipe
    """
    tmp_recipe = "hg19-gaps-v1"

    jdict = install.check_ggd_recipe(tmp_recipe,"genomics")
    assert type(jdict) == type(dict())
    assert jdict["packages"][tmp_recipe] 
    assert jdict["packages"][tmp_recipe]["identifiers"]["species"] == "Homo_sapiens"
    assert jdict["packages"][tmp_recipe]["identifiers"]["genome-build"] == "hg19"
    

def test_check_if_installed_recipe_not_installed():
    """
    Test if the check_if_installed function correclty identifies that the ggd data package is not installed.
    """

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
    recipe = "hg19-gaps-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-v1': {u'activate.d': 
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
    recipe = "hg19-gaps-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-v1': {u'activate.d': 
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

   
def test_check_conda_installation_pacakge_no_installed():
    """
    Test check conda instllation function correclty identifies that a data pacakges is not installed by conda
    """
    recipe = "Fake-hg19-gaps"
    version = "1"

    assert install.check_conda_installation(recipe,version) == False


def test_check_conda_installation_pacakge_no_installed_no_version_designation():
    """
    Test check conda instllation function correclty identifies that a data pacakges is not installed by conda
    """
    recipe = "Fake-hg19-gaps"
    version = "-1"

    assert install.check_conda_installation(recipe,version) == False


def test_check_conda_installation_pacakge_is_installed():
    """
    Test check conda instllation function correclty identifies that a data pacakges has been installed by conda.
     This method calls the install_hg19_gaps  to run.
    """
    recipe = "hg19-gaps-v1"
    version = install_hg19_gaps_v1()

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_conda_installation(recipe,version)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 


def test_check_conda_installation_pacakge_is_installed_noninstalled_version_desingation():
    """
    Test check conda instllation function correclty identifies that a data pacakges has been installed by conda.
     but that it has not installed the specied version
    """
    recipe = "hg19-gaps-v1"
    version = "9999"

    assert install.check_conda_installation(recipe,version) == False


def test_check_conda_installation_pacakge_is_installed_no_version_designation():
    """
    Test check conda instllation function correclty identifies that a data pacakges has been installed by conda.
     The version will be set to -1, meaning the version is not specified
    """
    recipe = "hg19-gaps-v1"
    version = "-1"

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_conda_installation(recipe,version)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 


def test_check_conda_installation_pacakge_no_installed_longer_package_name():
    """
    Test check conda instllation function correclty identifies that a data pacakges is not installed by conda
    """
    recipe = "hg19-gapsss-v1"
    version = "-1"

    assert install.check_conda_installation(recipe,version) == False


def test_check_conda_installation_pacakge_no_installed_shorter_package_name():
    """
    Test check conda instllation function correclty identifies that a data pacakges is not installed by conda
    """
    recipe = "hg19-ga"
    version = "-1"

    assert install.check_conda_installation(recipe,version) == False


def test_check_S3_bucket_not_uploaded():
    """
    Test if a recipe is cached on s3 or not. 
    """     
    recipe = "hg19-gaps-v1"

    ## If no tags key avaible return false
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-v1': {u'activate.d': 
                    False, u'version': u'1', u'post_link': True, u'binary_prefix': False, u'run_exports': {}, 
                    u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/hg19-gaps-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                    u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'hg19', u'species': u'Homo_sapiens'}}}}

    assert install.check_S3_bucket(recipe, ggd_jdict) == False

    ## If not cached key in tags return false 
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, 
                    u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': 
                    [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-v1-1-1.tar.bz2', 
                    u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', 
                    u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': 
                    u'Homo_sapiens'}}}}

    assert install.check_S3_bucket(recipe, ggd_jdict) == False

    ## If no "uploaded_to_aws" Signature in cached return false
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-v1': {u'activate.d': 
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
    recipe = "hg19-gaps-v1"
    ## Return True if uploaded to aws
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'hg19-gaps-v1': {u'activate.d': 
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
    uninstall_hg19_gaps_v1()

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
    name = "hg19-gaps-v1"
    ggd_channel = "genomics"
    default_version = "-1" 

    jdict = install.check_ggd_recipe(name,ggd_channel)

    assert install.install_from_cached(name, ggd_channel,jdict,default_version) == True   


def test_conda_install_bad_recipe():
    """
    Test that the conda_install function properly handels a bad recipe
    """

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
    uninstall_hg19_gaps_v1()
    name = "hg19-gaps-v1"
    ggd_channel = "genomics"

    ## Test with undesignated version
    default_version = "-1" 

    jdict = install.check_ggd_recipe(name,ggd_channel)

    assert install.conda_install(name, ggd_channel,jdict,default_version) == True   

    uninstall_hg19_gaps_v1()

    ## Test with designated version
    default_version = "1" 

    assert install.conda_install(name, ggd_channel,jdict,default_version) == True   


def test_get_file_location():
    """
    Test that get_file_location function to properly reterive the location of the ggd file
    """

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
    assert "A new environment variable that points to this directory path has also been created:" in output
    assert "$ggd_{}".format(ggd_recipe.replace("-","_")) in output


    ## The installed hg19-gaps-v1 recipe
    ggd_recipe = "hg19-gaps-v1"
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
    assert "A new environment variable that points to this directory path has also been created:" in output
    assert "$ggd_{}".format(ggd_recipe.replace("-","_")) in output


def test_install_main_function():
    """
    Test the main install function
    """

    ## Test a non ggd recipe
    ggd_recipe = "Fake-hg19-gaps"
    args = Namespace(channel='genomics', command='install', debug=False, name=ggd_recipe, version='-1')

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    ## Test an already installed ggd recipe
    install_hg19_gaps_v1()
    ggd_recipe = "hg19-gaps-v1"
    args = Namespace(channel='genomics', command='install', debug=False, name=ggd_recipe, version='-1')
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    ## Test a previously installed recipe, but the recipe path is broken 
    install_hg19_gaps_v1()
    ggd_recipe = "hg19-gaps-v1"
    args = Namespace(channel='genomics', command='install', debug=False, name=ggd_recipe, version='-1')

    jdict = install.check_ggd_recipe(ggd_recipe,"genomics")
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]
    CONDA_ROOT = utils.conda_root()
    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)
    for f in os.listdir(path):
        os.remove(os.path.join(path,f))
    os.rmdir(path)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    
    ## Install hg19-gaps-v1
    uninstall_hg19_gaps_v1()
    ggd_recipe = "hg19-gaps-v1"
    args = Namespace(channel='genomics', command='install', debug=False, name=ggd_recipe, version='-1')
    assert install.install((), args) == True


    
