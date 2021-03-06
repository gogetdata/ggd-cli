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
from helpers import CreateRecipe, install_hg19_gaps_ucsc_v1, uninstall_hg19_gaps_ucsc_v1
from ggd import install 
from ggd import utils
from ggd import uninstall
from ggd.utils import CondaEnvironmentNotFound 
from ggd.utils import get_conda_package_list
from ggd.utils import ChecksumError

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO


from conda.base.context import context
CONDA_ROOT = context.target_prefix

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
    if ggd_recipe in str(sp.check_output(["conda", "list"]).decode('utf8')):
        try:
            uninstall.uninstall((),Namespace(channel='genomics', command='uninstall', names=[ggd_recipe]))
            sp.check_output(["conda", "uninstall", "-y", ggd_recipe]) 
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
        install.check_ggd_recipe("hg19-gaps-ucsc-v1","ggd-fake-channel")
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
    
    assert install.check_if_installed(recipe,ggd_jdict) == False


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

    species = ggd_jdict["packages"][recipe]["identifiers"]["species"]
    build = ggd_jdict["packages"][recipe]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][recipe]["version"]
    
    CONDA_ROOT = utils.conda_root()

    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,recipe,version)

    path_added = False
    if not glob.glob(path):
        os.makedirs(path)
        path_added = True
    
    ## If a package is installed, check_if_installed returns True
    assert install.check_if_installed(recipe,ggd_jdict) == True

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
    
    assert install.check_if_installed(recipe,ggd_jdict,prefix=temp_env) == False

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

    species = ggd_jdict["packages"][ggd_package]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_package]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_package]["version"]

    ## If a package is installed, check_if_installed returns True
    assert install.check_if_installed(ggd_package,ggd_jdict,prefix=temp_env) == True

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


def test_check_conda_installation_pacakge_is_installed():
    """
    Test check conda instllation function correclty identifies that a data pacakges has been installed by conda.
     This method calls the install_hg19_gaps  to run.
    """
    pytest_enable_socket()

    ## Install hg19-gaps-ucsc-v1
    recipe = "hg19-gaps-ucsc-v1"
    args = Namespace(channel='genomics', command='install', debug=False, name=[recipe], file=[] , prefix=None, id = None)
    try:
        install.install((), args)
    except SystemExit:
        pass
    jdict = install.check_ggd_recipe(recipe,"genomics")
    version = jdict["packages"][recipe]["version"]
    

    ## Test that it is already installed
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_conda_installation(recipe)
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

    assert install.check_conda_installation(recipe) == False


def test_check_conda_installation_pacakge_no_installed_shorter_package_name():
    """
    Test check conda instllation function correclty identifies that a data pacakges is not installed by conda
    """
    pytest_enable_socket()

    recipe = "hg19-ga"

    assert install.check_conda_installation(recipe) == False


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

    assert install.check_conda_installation(ggd_package,prefix=temp_env) == False


    ## Check that an installed data package is stated as such
    sp.check_output(["ggd", "install", "--prefix", temp_env, ggd_package])

    species = ggd_jdict["packages"][ggd_package]["identifiers"]["species"]
    build = ggd_jdict["packages"][ggd_package]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"][ggd_package]["version"]
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.check_conda_installation(ggd_package,prefix=temp_env) 
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


def test_get_idname_from_metarecipe():
    """
    Method to test if the get_idname_from_metarecipe() correctly returns the right name
    """

    accession_id = "GSE123"
    meta_recipe = "meta-recipe-geo-accession-geo-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'meta-recipe-geo-accession-geo-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'', u'data-provider': u'GEO'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/meta-recipe-geo-accession-geo-v1-1-0.tar.bz2', u'pre_link': False, u'keywords': [u'GEO', u'Gene Expression Omnibus'], 
                    u'summary': u'GEO Meta-Recipe', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'meta-recipe', u'species': u'meta-recipe'}}}}

    new_name = install.get_idname_from_metarecipe(accession_id,  meta_recipe, ggd_jdict)

    ## This method does not change case
    assert new_name != "gse123-geo-v1"
    assert new_name == "GSE123-geo-v1"


    accession_id = "gds456"
    meta_recipe = "meta-recipe-geo-accession-geo-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'meta-recipe-geo-accession-geo-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'', u'data-provider': u'GEO'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/meta-recipe-geo-accession-geo-v1-1-0.tar.bz2', u'pre_link': False, u'keywords': [u'GEO', u'Gene Expression Omnibus'], 
                    u'summary': u'GEO Meta-Recipe', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'meta-recipe', u'species': u'meta-recipe'}}}}

    new_name = install.get_idname_from_metarecipe(accession_id,  meta_recipe, ggd_jdict)

    ## This method does not change case
    assert new_name == "gds456-geo-v1"


    accession_id = "GsM99890"
    meta_recipe = "meta-recipe-geo-accession-geo-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'meta-recipe-geo-accession-geo-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'', u'data-provider': u'GEO'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/meta-recipe-geo-accession-geo-v1-1-0.tar.bz2', u'pre_link': False, u'keywords': [u'GEO', u'Gene Expression Omnibus'], 
                    u'summary': u'GEO Meta-Recipe', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'meta-recipe', u'species': u'meta-recipe'}}}}

    new_name = install.get_idname_from_metarecipe(accession_id,  meta_recipe, ggd_jdict)

    ## This method does not change case
    assert new_name == "GsM99890-geo-v1"


    accession_id = "GsM99890"
    meta_recipe = "meta-recipe-geo-accession-geo-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'meta-recipe-geo-accession-geo-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'', u'data-provider': u'THE-DATA-PROVIDER'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/meta-recipe-geo-accession-geo-v1-1-0.tar.bz2', u'pre_link': False, u'keywords': [u'GEO', u'Gene Expression Omnibus'], 
                    u'summary': u'GEO Meta-Recipe', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'meta-recipe', u'species': u'meta-recipe'}}}}

    new_name = install.get_idname_from_metarecipe(accession_id,  meta_recipe, ggd_jdict)

    ## Test that the data provider is changed to lower case 
    assert new_name == "GsM99890-the-data-provider-v1"


    accession_id = "GsM99890"
    meta_recipe = "meta-recipe-geo-accession-geo-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'meta-recipe-geo-accession-geo-v1': {u'activate.d': 
                    False, u'version': u'THE-VERSION', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'', u'data-provider': u'geo'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/meta-recipe-geo-accession-geo-v1-1-0.tar.bz2', u'pre_link': False, u'keywords': [u'GEO', u'Gene Expression Omnibus'], 
                    u'summary': u'GEO Meta-Recipe', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'meta-recipe', u'species': u'meta-recipe'}}}}

    new_name = install.get_idname_from_metarecipe(accession_id,  meta_recipe, ggd_jdict)

    ## Test that the version is properly used
    assert new_name == "GsM99890-geo-vTHE-VERSION"


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
    jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                {u'activate.d': False, u'version': u'1', u'tags': {u'cached': ["uploaded_to_aws"], u'ggd-channel': u'genomics', 
                u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                u'hg19', u'species': u'Homo_sapiens'}}}}
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install_from_cached([name], ggd_channel,jdict)   
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    ## Good Install 
    name = "hg19-cpg-islands-ucsc-v1"
    ggd_channel = "genomics"

    jdict = install.check_ggd_recipe(name,ggd_channel)

    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()
    assert install.install_from_cached([name], ggd_channel,jdict) == True   

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
        args = Namespace(channel='genomics', command='uninstall', names=[name])
        uninstall.uninstall((),args)
    except:
        pass


    ## Test with multiple in the list
    ggd_recipes = ["grch37-chromsizes-ggd-v1","hg19-chromsizes-ggd-v1"]

    assert install.install_from_cached(ggd_recipes, ggd_channel,jdict) == True   
    for name in ggd_recipes:
        pkg_info = get_conda_package_list(utils.conda_root(),name)
        version = pkg_info[name]["version"]
        build = pkg_info[name]["build"]
        assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","noarch"))
        assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","noarch",name+"-{}-{}.tar.bz2".format(version,build)))
        assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","channeldata.json"))
        with open(os.path.join(utils.conda_root(),"share","ggd_info","channeldata.json")) as jfile:
            channeldata = json.load(jfile)
            assert name in channeldata["packages"]

    for name in ggd_recipes:
        args = Namespace(channel='genomics', command='uninstall', names=[name])
        assert uninstall.uninstall((),args) == True


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
    jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                {u'activate.d': False, u'version': u'1', u'tags': {u'cached': ["uploaded_to_aws"], u'ggd-channel': u'genomics', 
                u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                u'hg19', u'species': u'Homo_sapiens'}}}}
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.install_from_cached([name], ggd_channel,jdict,prefix=temp_env)   
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 


    ## Good install 
    name = "hg19-pfam-domains-ucsc-v1"
    ggd_channel = "genomics"
    jdict = install.check_ggd_recipe(name,ggd_channel)

    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()

    assert install.install_from_cached([name], ggd_channel,jdict,prefix=temp_env) == True   

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
    jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Fake_hg19-gaps': 
                {u'activate.d': False, u'version': u'1', u'tags': {u'cached': ["uploaded_to_aws"], u'ggd-channel': u'genomics', 
                u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': 
                {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                u'noarch/Fake-hg19-gaps-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], 
                u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': 
                u'hg19', u'species': u'Homo_sapiens'}}}}

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        install.conda_install([name], ggd_channel,jdict)    
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

    jdict = install.check_ggd_recipe(name,ggd_channel)

    species = jdict["packages"][name]["identifiers"]["species"]
    build = jdict["packages"][name]["identifiers"]["genome-build"]
    version = jdict["packages"][name]["version"]

    assert install.conda_install([name], ggd_channel,jdict) == True   

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

    #### Uninstall package
    args = Namespace(channel='genomics', command='uninstall', names=[name])
    uninstall.uninstall((),args)

    ## Test with multiple in the list
    ggd_recipes = ["grch38-chromsizes-ggd-v1","hg38-chromsizes-ggd-v1"]

    assert install.conda_install(ggd_recipes, ggd_channel,jdict) == True   
    for name in ggd_recipes:
        pkg_info = get_conda_package_list(utils.conda_root(),name)
        version = pkg_info[name]["version"]
        build = pkg_info[name]["build"]
        assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","noarch"))
        assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","noarch",name+"-{}-{}.tar.bz2".format(version,build)))
        assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd_info","channeldata.json"))
        with open(os.path.join(utils.conda_root(),"share","ggd_info","channeldata.json")) as jfile:
            channeldata = json.load(jfile)
            assert name in channeldata["packages"]

    args = Namespace(channel='genomics', command='uninstall', names=ggd_recipes)
    assert uninstall.uninstall((),args) == True


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
    jdict = install.check_ggd_recipe(name,ggd_channel)

    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()

    assert install.conda_install([name], ggd_channel,jdict,prefix=temp_env) == True   

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


def test_conda_install_meta_recipe():
    """
    Test that the conda_install() method correctly install a meta recipe. 
    """

    import tarfile 
    import tempfile
    from ggd import check_recipe

    tmpdir = tempfile.mkdtemp()

    recipe_path = os.path.join(tmpdir,"gse123-geo-v1")
    os.mkdir(recipe_path)

    ## Download files
    try:
        ## checkusm
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/checksums_file.txt",
                         "--directory-prefix",
                         recipe_path])
        ##  meta.yaml
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/meta.yaml",
                         "--directory-prefix",
                         recipe_path])
        ##  metarecipe.sh
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/metarecipe.sh",
                         "--directory-prefix",
                         recipe_path])
        ## head parser
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/parse_geo_header.py",
                         "--directory-prefix",
                         recipe_path])
        ## Post link
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/post-link.sh", 
                         "--directory-prefix",
                         recipe_path])
        ## recipe.sh
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/recipe.sh",
                         "--directory-prefix",
                         recipe_path])

    except sp.CalledProcessError as e:
        print(str(e))
        assert False

    ## update the name
    for f in os.listdir(recipe_path):
        content = [x.replace("meta-recipe-geo-accession-geo-v1","gse123-geo-v1") for x in open(os.path.join(recipe_path,f))]
        with open(os.path.join(recipe_path,f), "w") as out:
            out.write("".join(content))

    ## Original yaml
    orig_yaml = yaml.safe_load(open(os.path.join(recipe_path, "meta.yaml")))
    tarball_file_path = check_recipe._build(recipe_path,orig_yaml)
    assert os.path.isfile(tarball_file_path)

    ## Set up chanel metadata dict
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'gse123-geo-v1': {u'activate.d': 
                    False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                    u'', u'data-provider': u'GEO'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                    False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/gse123-geo-v1-1-0.tar.bz2', u'pre_link': False, u'keywords': [u'GEO', u'Gene Expression Omnibus'], 
                    u'summary': u'GEO Meta-Recipe', u'text_prefix': False, u'identifiers': {u'genome-build': 
                    u'meta-recipe', u'species': u'meta-recipe'}}}}


    ## Test installing a meta recipe wihtout a meta=recipe designation 
    passed = False
    try:
        install.conda_install(ggd_recipes=["gse123-geo-v1"], 
                              ggd_channel = "genomics",
                              ggd_jdict = ggd_jdict,
                              debug = False,
                              prefix = None,
                              meta_recipe = False,
                              meta_recipe_name = "meta-recipe-geo-accession-v1")
        passed = True
    except SystemExit as e:
        pass
    except Exception as e:
        assert False

    assert not passed 


    ## Test meta recipe with no env vars added
    env_var_tmp_dir, env_var_file_path, final_commands_files = utils.create_tmp_meta_recipe_env_file()

    ## Set environ vars
    os.environ["GGD_METARECIPE_ID"] = "GSE123"
    os.environ["GGD_METARECIPE_ENV_VAR_FILE"] = env_var_file_path 
    os.environ["GGD_METARECIPE_FINAL_COMMANDS_FILE"] = final_commands_files

    ## Test that the recipe is installed, the recipe.sh file is upadated, and the meta.yaml file is updated
    assert install.conda_install(ggd_recipes=["gse123-geo-v1"], 
                                 ggd_channel = "genomics",
                                 ggd_jdict = ggd_jdict,
                                 debug = False,
                                 prefix = None,
                                 meta_recipe = True,
                                 meta_recipe_name = "meta-recipe-geo-accession-v1")
    
    
    recipe_contents = ""
    yaml_dict = {}
    with tarfile.open(os.path.join(utils.conda_root(),"pkgs",os.path.basename(tarball_file_path)), mode="r|bz2") as tf:
        for info in tf:
            if info.name == "info/recipe/recipe.sh":
                recipe_contents = tf.extractfile(info)
                recipe_contents = recipe_contents.read().decode()

            elif info.name == "info/recipe/meta.yaml.template":
                yaml_dict = tf.extractfile(info)
                yaml_dict = yaml.safe_load(yaml_dict.read().decode())

    ## Check the recipe contents
    assert recipe_contents == (
"""
curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/soft/GSE123_family.soft.gz" -O -J --silent

curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/matrix/GSE123_series_matrix.txt.gz" -O -J --silent

curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/suppl/GSE123_RAW.tar" -O -J --silent

tar -xf GSE123_RAW.tar
""")
    
    ## check the yaml file
    assert yaml_dict["build"]["noarch"] == orig_yaml["build"]["noarch"] 
    assert yaml_dict["build"]["number"] == orig_yaml["build"]["number"] 
    assert yaml_dict["package"]["name"] == orig_yaml["package"]["name"] 
    assert yaml_dict["package"]["version"] == orig_yaml["package"]["version"] 
    assert yaml_dict["about"]["identifiers"]["genome-build"] == orig_yaml["about"]["identifiers"]["genome-build"] 
    assert yaml_dict["about"]["identifiers"]["species"] == orig_yaml["about"]["identifiers"]["species"]
    assert "updated-species" in yaml_dict["about"]["identifiers"]
    assert yaml_dict["about"]["identifiers"]["updated-species"] == "Mus musculus"
    assert "parent-meta-recipe" in yaml_dict["about"]["identifiers"]
    assert yaml_dict["about"]["identifiers"]["parent-meta-recipe"] == "meta-recipe-geo-accession-v1"
    assert yaml_dict["about"]["keywords"] != orig_yaml["about"]["keywords"] 
    assert yaml_dict["about"]["summary"] != orig_yaml["about"]["summary"] 
    assert yaml_dict["about"]["tags"]["data-provider"] == orig_yaml["about"]["tags"]["data-provider"] 
    assert yaml_dict["about"]["tags"]["data-version"] != orig_yaml["about"]["tags"]["data-version"] 
    assert yaml_dict["about"]["tags"]["genomic-coordinate-base"] == orig_yaml["about"]["tags"]["genomic-coordinate-base"] 

    ## Check the installed files
    species = "meta-recipe"
    build = "meta-recipe"
    name = "gse123-geo-v1"
    version = "1"
    assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_family.soft.gz"))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_series_matrix.txt.gz")) ## From TAR file
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSM3227_jzo026-rp1-v5-u74av2.CEL.gz")) ## From TAR file
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSM3225_jzo016-rp1-v5-u74av2.CEL.gz")) ## From TAR file
    assert not os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_RAW.tar")) ## Tar file should not exists after install it 

    ## remove the temp dir
    if os.path.exists(env_var_tmp_dir):
        shutil.rmtree(env_var_tmp_dir)

    ## uninstall
    sp.check_call(["ggd","uninstall","gse123-geo-v1"])
        

    ## Check different prefix
    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_meta_recipe")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_meta_recipe"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "temp_meta_recipe"])

    ## Build the recipe
    tarball_file_path = check_recipe._build(recipe_path,orig_yaml)
    assert os.path.isfile(tarball_file_path)

    ## Test meta recipe with no env vars added
    env_var_tmp_dir, env_var_file_path, final_commands_files = utils.create_tmp_meta_recipe_env_file()

    ## Set environ vars
    os.environ["GGD_METARECIPE_ID"] = "GSE123"
    os.environ["GGD_METARECIPE_ENV_VAR_FILE"] = env_var_file_path 
    os.environ["GGD_METARECIPE_FINAL_COMMANDS_FILE"] = final_commands_files
    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()

    assert install.conda_install(ggd_recipes=["gse123-geo-v1"], 
                                 ggd_channel = "genomics",
                                 ggd_jdict = ggd_jdict,
                                 debug = False,
                                 prefix = temp_env,
                                 meta_recipe = True,
                                 meta_recipe_name = "meta-recipe-geo-accession-v1")

    recipe_contents = ""
    yaml_dict = {}
    with tarfile.open(os.path.join(temp_env,"pkgs",os.path.basename(tarball_file_path)), mode="r|bz2") as tf:
        for info in tf:
            if info.name == "info/recipe/recipe.sh":
                recipe_contents = tf.extractfile(info)
                recipe_contents = recipe_contents.read().decode()

            elif info.name == "info/recipe/meta.yaml.template":
                yaml_dict = tf.extractfile(info)
                yaml_dict = yaml.safe_load(yaml_dict.read().decode())

    ## Check the recipe contents
    assert recipe_contents == (
"""
curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/soft/GSE123_family.soft.gz" -O -J --silent

curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/matrix/GSE123_series_matrix.txt.gz" -O -J --silent

curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/suppl/GSE123_RAW.tar" -O -J --silent

tar -xf GSE123_RAW.tar
""")
    
    ## check the yaml file
    assert yaml_dict["build"]["noarch"] == orig_yaml["build"]["noarch"] 
    assert yaml_dict["build"]["number"] == orig_yaml["build"]["number"] 
    assert yaml_dict["package"]["name"] == orig_yaml["package"]["name"] 
    assert yaml_dict["package"]["version"] == orig_yaml["package"]["version"] 
    assert yaml_dict["about"]["identifiers"]["genome-build"] == orig_yaml["about"]["identifiers"]["genome-build"] 
    assert yaml_dict["about"]["identifiers"]["species"] == orig_yaml["about"]["identifiers"]["species"]
    assert "updated-species" in yaml_dict["about"]["identifiers"]
    assert yaml_dict["about"]["identifiers"]["updated-species"] == "Mus musculus"
    assert "parent-meta-recipe" in yaml_dict["about"]["identifiers"]
    assert yaml_dict["about"]["identifiers"]["parent-meta-recipe"] == "meta-recipe-geo-accession-v1"
    assert yaml_dict["about"]["keywords"] != orig_yaml["about"]["keywords"] 
    assert yaml_dict["about"]["summary"] != orig_yaml["about"]["summary"] 
    assert yaml_dict["about"]["tags"]["data-provider"] == orig_yaml["about"]["tags"]["data-provider"] 
    assert yaml_dict["about"]["tags"]["data-version"] != orig_yaml["about"]["tags"]["data-version"] 
    assert yaml_dict["about"]["tags"]["genomic-coordinate-base"] == orig_yaml["about"]["tags"]["genomic-coordinate-base"] 

    ## Check the installed files
    species = "meta-recipe"
    build = "meta-recipe"
    name = "gse123-geo-v1"
    version = "1"
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,name,version))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSE123_family.soft.gz"))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSE123_series_matrix.txt.gz")) ## From TAR file
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSM3227_jzo026-rp1-v5-u74av2.CEL.gz")) ## From TAR file
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSM3225_jzo016-rp1-v5-u74av2.CEL.gz")) ## From TAR file
    assert not os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSE123_RAW.tar")) ## Tar file should not exists after install it 

    ## Check that the recipe was not installed in the current environment
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_family.soft.gz")) == False
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_series_matrix.txt.gz")) == False
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSM3227_jzo026-rp1-v5-u74av2.CEL.gz")) == False 
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSM3225_jzo016-rp1-v5-u74av2.CEL.gz")) == False 

    ## Test that the tarfile and the pkg dir were correctly copied to the prefix
    data_packages = get_conda_package_list(temp_env, include_local = True)
    version = str(data_packages[name]["version"])
    build_number = str(data_packages[name]["build"])
    tarfile = "{}-{}-{}.tar.bz2".format(name,version,build_number)
    pkgdir = "{}-{}-{}".format(name,version,build_number)

    assert os.path.isfile(os.path.join(temp_env,"pkgs",tarfile))
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir))

    ### Test that the ggd_info metadata is updated with ggd pkg
    pkg_info = get_conda_package_list(temp_env,name, include_local = True)
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
    sp.check_output(["conda", "env", "remove", "--name", "temp_meta_recipe"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False

    ## remove the temp dir
    if os.path.exists(env_var_tmp_dir):
        shutil.rmtree(env_var_tmp_dir)

    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)


def test_get_file_location():
    """
    Test that get_file_location function to properly reterive the location of the ggd file
    """
    pytest_enable_socket()

    ## Fake recipe
    ggd_recipe = "Fake_hg19-gaps"
    ggd_channel = "genomics"
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
        install.get_file_locations([ggd_recipe],jdict)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: There was an error during installation" in output
    assert ":ggd:install: Installed file locations" in output
    assert ggd_recipe in output 
    assert "$ggd_{}_dir".format(ggd_recipe.replace("-","_")) not in output
    assert "$ggd_{}_file".format(ggd_recipe.replace("-","_")) not in output


    ggd_recipe = "grch37-chromsizes-ggd-v1"
    ggd_channel = "genomics"
    jdict = install.check_ggd_recipe(ggd_recipe,ggd_channel)
    
    assert install.install_from_cached([ggd_recipe], ggd_channel,jdict) == True   

    jdict = install.check_ggd_recipe(ggd_recipe,ggd_channel)
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]
    CONDA_ROOT = utils.conda_root()
    path = os.path.join(CONDA_ROOT,"share","ggd",species,build,ggd_recipe,version)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        install.get_file_locations([ggd_recipe],jdict)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: Installed file locations" in output
    assert ggd_recipe in output 
    assert "$ggd_{}_dir".format(ggd_recipe.replace("-","_")) in output
    assert "$ggd_{}_file".format(ggd_recipe.replace("-","_")) in output
    assert path in output

    try:
        args = Namespace(channel='genomics', command='uninstall', names=[ggd_recipe])
        uninstall.uninstall((),args)
    except:
        pass


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

    jdict = install.check_ggd_recipe(ggd_recipe,ggd_channel)
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]

    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()
    assert install.install_from_cached([ggd_recipe], ggd_channel,jdict,prefix=temp_env) == True   

    path = os.path.join(temp_env,"share","ggd",species,build,ggd_recipe,version)

    ### Test output from get file location
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        install.get_file_locations([ggd_recipe],jdict,prefix=temp_env)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: Installed file locations" in output
    assert ggd_recipe in output 
    assert "$ggd_{}_dir".format(ggd_recipe.replace("-","_")) in output
    assert "$ggd_{}_file".format(ggd_recipe.replace("-","_")) in output
    assert path in output
    assert ":ggd:install: NOTE: These environment variables are specific to the {p} conda environment and can only be accessed from within that environment".format(p=temp_env) in output

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


def test_install_checksum():
    """
    Test the install_checksum method 
    """
    pytest_enable_socket()


    ## Create test recipe
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
                - genome
                final-file-sizes:
                  hg19-chromsizes-ggd-v1.txt: 1.99K
                final-files: 
                - trial-recipe-v1.genome
                ggd-channel: genomics
        
        recipe.sh: |
            #!/bin/sh
            set -eo pipefail -o nounset

            wget https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/Homo_sapiens/hg19/hg19.genome
        
        post-link.sh: |
            set -eo pipefail -o nounset

            if [[ -z $(conda info --envs | grep "*" | grep -o "\/.*") ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-recipe-v1/1
            elif [[ $(conda info --envs | grep "*" | grep -o "\/.*") == "base" ]]; then
                export CONDA_ROOT=$(conda info --root)
                env_dir=$CONDA_ROOT
                export RECIPE_DIR=$CONDA_ROOT/share/ggd/Homo_sapiens/hg38/trial-recipe-v1/1
            else
                env_dir=$(conda info --envs | grep "*" | grep -o "\/.*")
                export CONDA_ROOT=$env_dir
                export RECIPE_DIR=$env_dir/share/ggd/Homo_sapiens/hg38/trial-recipe-v1/1
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
                (mv $f "trial-recipe-v1.$ext")
            done

            ## Add environment variables 
            #### File
            if [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 1 ]] ## If only one file
            then
                recipe_env_file_name="ggd_trial-recipe-v1_file"
                recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                file_path="$(find $RECIPE_DIR -type f -maxdepth 1)"

            elif [[ `find $RECIPE_DIR -type f -maxdepth 1 | wc -l | sed 's/ //g'` == 2 ]] ## If two files
            then
                indexed_file=`find $RECIPE_DIR -type f \( -name "*.tbi" -or -name "*.fai" -or -name "*.bai" -or -name "*.crai" -or -name "*.gzi" \) -maxdepth 1`
                if [[ ! -z "$indexed_file" ]] ## If index file exists
                then
                    recipe_env_file_name="ggd_trial-recipe-v1_file"
                    recipe_env_file_name="$(echo "$recipe_env_file_name" | sed 's/-/_/g')"
                    file_path="$(echo $indexed_file | sed 's/\.[^.]*$//')" ## remove index extension
                fi  
            fi 

            #### Dir
            recipe_env_dir_name="ggd_trial-recipe-v1_dir"
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
            trial-recipe-v1.genome\t54416e6d1884e0178e5819fbd4f3a38f

    """, from_string=True)

    recipe.write_recipes()

    from ggd import check_recipe

    ## Check if the recipe is already installed
    if "trail-recipe-v1" in sp.check_output(["conda list {}".format("trail-recipe-v1")], shell=True).decode("utf8"):
        sp.check_output(["conda uninstall trail-recipe-v1 -y"], shell = True)
    ## Create recipe
    recipe_dir_path = recipe.recipe_dirs["trial-recipe-v1"] 
    ## Remove checksum file
    #os.remove(os.path.join(recipe_dir_path,"checksums_file.txt"))
    ## build tar.bz2 file and install 
    yaml_file = yaml.safe_load(open(os.path.join(recipe_dir_path, "meta.yaml")))
    tarball_file_path = check_recipe._build(recipe_dir_path,yaml_file)
    assert os.path.isfile(tarball_file_path)
    ## Install recipe
    assert check_recipe._install(tarball_file_path, "trial-recipe-v1") == True

    
    ## Fake ggd_jdict
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'trial-recipe-v1': 
                    {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', 
                    u'data-version': u'11-Mar-2019',u'file-type':u'bed',u'final-files':[u'trial-recipe-v1.genome']}, 
                    u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, 
                    u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/trial-recipe-v1-1-1.tar.bz2', 
                    u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'hg38 Assembly gaps from USCS', 
                    u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}


    ## Test good checksum
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        install.install_checksum(["trial-recipe-v1"],ggd_jdict)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: Checksum for trial-recipe-v1" in output
    assert ":ggd:checksum: installed  file checksum: trial-recipe-v1.genome checksum: 54416e6d1884e0178e5819fbd4f3a38f" in output
    assert ":ggd:checksum: metadata checksum record: trial-recipe-v1.genome checksum: 54416e6d1884e0178e5819fbd4f3a38f" in output
    assert ":ggd:install: ** Successful Checksum **" in output

    ## Create fake recipes
    fakerecipe = CreateRecipe(
    """

    trial_recipe_dir1: 
        info: 
            recipe:
                checksums_file.txt: |
                    trial-recipe-v1.genome\taj09f239a;ojveiaj289j

    trial_recipe_dir2: 
        info: 
            recipe:
                bad_checksums_file.txt: |
                    not a real checksum file
            

    """, from_string=True)

    fakerecipe.write_nested_recipes()

    trial_recipe1_path = fakerecipe.recipe_dirs["trial_recipe_dir1"]
    trial_recipe2_path = fakerecipe.recipe_dirs["trial_recipe_dir2"]

    if os.path.exists(os.path.join(utils.conda_root(),"pkgs","trial-recipe-v1-1-0.tar.bz2")):
        os.remove(os.path.join(utils.conda_root(),"pkgs","trial-recipe-v1-1-0.tar.bz2"))

    import tarfile
    tar = tarfile.open(os.path.join(utils.conda_root(),"pkgs","trial-recipe-v1-1-0.tar.bz2"), "w:bz2")
    tar.add(trial_recipe2_path, arcname=(""))
    tar.close()

    ## Test a tar.bz2 without checksum file 
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        install.install_checksum(["trial-recipe-v1"],ggd_jdict)
    output2 = temp_stdout.getvalue().strip() 
    assert ":ggd:install: WARNING: Checksum file not available for the trial-recipe-v1 data package. Data file content validation will be skipped" in output2


    ## Bad checksum 
    tar = tarfile.open(os.path.join(utils.conda_root(),"pkgs","trial-recipe-v1-1-0.tar.bz2"), "w:bz2")
    tar.add(trial_recipe1_path, arcname=(""))
    tar.close()

    try:
        install.install_checksum(["trial-recipe-v1"],ggd_jdict)
        assert False
    except ChecksumError as e:
        assert "Data file content validation failed. The trial-recipe-v1 data package did not install correctly" in str(e)
    except Exception as e:
        print(str(e))
        assert False


    ## Test without installed files in it
    ## Get install path
    species = ggd_jdict["packages"]["trial-recipe-v1"]["identifiers"]["species"]
    build = ggd_jdict["packages"]["trial-recipe-v1"]["identifiers"]["genome-build"]
    version = ggd_jdict["packages"]["trial-recipe-v1"]["version"]
    install_path = os.path.join(utils.conda_root(),"share","ggd",species,build,"trial-recipe-v1",version)

    shutil.rmtree(install_path)

    try:
        install.install_checksum(["trial-recipe-v1"],ggd_jdict)
        assert False
    except ChecksumError as e:
        assert "Data file content validation failed. The trial-recipe-v1 data package did not install correctly" in str(e)
    except Exception:
        print(str(e))
        assert False

    sp.check_output(["conda","uninstall", "-y", "trial-recipe-v1"])


#    ## Test a good checksum 
#    recipe = "grch37-chromsizes-ggd-v1"
#    args = Namespace(channel='genomics', command='install', debug=False, name=[recipe], file=[], prefix=None)
#    assert install.install((), args) == True
#
#    ggd_jdict = install.check_ggd_recipe(recipe,"genomics")
#
#    temp_stdout = StringIO()
#    with redirect_stdout(temp_stdout):
#        install.install_checksum([recipe],ggd_jdict)
#    output = temp_stdout.getvalue().strip() 
#    assert ":ggd:install: Checksum for grch37-chromsizes-ggd-v1" in output
#    assert ":ggd:checksum: installed  file checksum: grch37-chromsizes-ggd-v1.txt checksum: 9035fb43d5341584a8b11fb70de3fae5" in output
#    assert ":ggd:checksum: metadata checksum record: grch37-chromsizes-ggd-v1.txt checksum: 9035fb43d5341584a8b11fb70de3fae5" in output
#    assert ":ggd:install: ** Successful Checksum **" in output
#
#
#    try:
#        args = Namespace(channel='genomics', command='uninstall', names=[recipe])
#        uninstall.uninstall((),args)
#    except:
#        pass
    

def test_install_checksum_meta_recipe():
    """
    Test the the checksum is skipped when installing a meta-recipe
    """

    pytest_enable_socket()

    import tempfile
    from ggd import check_recipe

    tmpdir = tempfile.mkdtemp()

    recipe_path = os.path.join(tmpdir, "gse123-geo-v1")
    os.mkdir(recipe_path)

    ## Download files
    try:
       ## checkusm
       sp.check_call(["wget", 
                        "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/checksums_file.txt",
                        "--directory-prefix",
                        recipe_path])
       ##  meta.yaml
       sp.check_call(["wget", 
                        "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/meta.yaml",
                        "--directory-prefix",
                        recipe_path])
       ##  metarecipe.sh
       sp.check_call(["wget", 
                        "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/metarecipe.sh",
                        "--directory-prefix",
                        recipe_path])
       ## head parser
       sp.check_call(["wget", 
                        "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/parse_geo_header.py",
                        "--directory-prefix",
                        recipe_path])
       ## Post link
       sp.check_call(["wget", 
                        "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/post-link.sh", 
                        "--directory-prefix",
                        recipe_path])
       ## recipe.sh
       sp.check_call(["wget", 
                        "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/recipe.sh",
                        "--directory-prefix",
                        recipe_path])

    except sp.CalledProcessError as e:
       print(str(e))
       assert False

    ## update the name
    for f in os.listdir(recipe_path):
       content = [x.replace("meta-recipe-geo-accession-geo-v1","gse123-geo-v1") for x in open(os.path.join(recipe_path,f))]
       with open(os.path.join(recipe_path,f), "w") as out:
           out.write("".join(content))


    ## Set env vars
    env_var_tmp_dir, env_var_file_path, final_commands_files = utils.create_tmp_meta_recipe_env_file()

    ## Set environ vars
    os.environ["GGD_METARECIPE_ID"] = "GSE123"
    os.environ["GGD_METARECIPE_ENV_VAR_FILE"] = env_var_file_path 
    os.environ["GGD_METARECIPE_FINAL_COMMANDS_FILE"] = final_commands_files


    ## Get yaml file
    yaml_file = yaml.safe_load(open(os.path.join(recipe_path, "meta.yaml")))
    tarball_file_path = check_recipe._build(recipe_path,yaml_file)
    assert os.path.isfile(tarball_file_path)
    ## Install recipe
    assert check_recipe._install(tarball_file_path, "gse123-geo-v1") == True


    ## Remove the temp directories
    if os.path.exists(tmpdir):
       shutil.rmtree(tmpdir)

    if os.path.exists(env_var_tmp_dir):
       shutil.rmtree(env_var_tmp_dir)


    ## Get recipe info
    meta_recipe = "gse123-geo-v1"
    parent_meta_recipe = "meta-recipe-geo-accession-geo-v1"
    ggd_jdict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'gse123-geo-v1': {u'activate.d': 
                   False, u'version': u'1', u'tags': {u'cached': [], u'ggd-channel': u'genomics', u'data-version': 
                   u'', u'data-provider': u'GEO'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': 
                   False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                   u'noarch/gse123-geo-v1-1-0.tar.bz2', u'pre_link': False, u'keywords': [u'GEO', u'Gene Expression Omnibus'], 
                   u'summary': u'GSE123 GEO Meta-Recipe', u'text_prefix': False, u'identifiers': {u'genome-build': 
                   u'meta-recipe', u'species': u'meta-recipe'}}}}


    ## Test wihtout parent_name
    try:
       install.install_checksum(pkg_names = [meta_recipe],
                                ggd_jdict = ggd_jdict,
                                prefix = utils.conda_root(),
                                meta_recipe = True,
                                meta_recipe_name = "")
       assert False
    except AssertionError as e:
       assert ":ggd:install: !!ERROR!! Unable to preform checksum on a meta-recipe without the parent meta-recipe name" in str(e)


    ## Test good checksum
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):

       install.install_checksum(pkg_names = [meta_recipe],
                                ggd_jdict = ggd_jdict,
                                prefix = utils.conda_root(),
                                meta_recipe = True,
                                meta_recipe_name = parent_meta_recipe)

    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: Initiating data file content validation using checksum" in output
    assert ":ggd:install: Checksum for {}".format(meta_recipe) in output
    assert ":ggd:install: NOTICE: Skipping checksum for meta-recipe {} => {}".format(parent_meta_recipe, meta_recipe) in output

    sp.check_call(["ggd","uninstall","gse123-geo-v1"])


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
    jdict = install.check_ggd_recipe(ggd_recipe,ggd_channel)

    os.environ["CONDA_SOURCE_PREFIX"] = utils.conda_root()
    assert install.install_from_cached([ggd_recipe], ggd_channel,jdict,prefix=temp_env) == True   

    ## Test a prefix that is the same and the conda root returns False
    assert install.copy_pkg_files_to_prefix(utils.conda_root(),[ggd_recipe]) == False

    ## Extra info
    data_packages = get_conda_package_list(temp_env)
    version = str(data_packages[ggd_recipe]["version"])
    build = str(data_packages[ggd_recipe]["build"])

    ## Test that the files were properly copied
    tarfile = "{}-{}-{}.tar.bz2".format(ggd_recipe,version,build)
    pkgdir = "{}-{}-{}".format(ggd_recipe,version,build)
    assert os.path.isfile(os.path.join(temp_env,"pkgs",tarfile)) == True
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir)) == True

    ## Remove them from the target prefix
    os.remove(os.path.join(temp_env,"pkgs",tarfile))
    shutil.rmtree(os.path.join(temp_env,"pkgs",pkgdir))
    assert os.path.isfile(os.path.join(temp_env,"pkgs",tarfile)) == False
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir)) == False

    ### Test the function passes
    assert install.copy_pkg_files_to_prefix(temp_env,[ggd_recipe]) == True

    ### Test the files are correct
    assert os.path.isfile(os.path.join(utils.conda_root(),"pkgs",tarfile))
    assert os.path.isdir(os.path.join(utils.conda_root(),"pkgs",pkgdir))
    assert os.path.isfile(os.path.join(temp_env,"pkgs",tarfile))
    assert os.path.isdir(os.path.join(temp_env,"pkgs",pkgdir))

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env6"])
    try:
       shutil.rmtree(temp_env)
    except Exception:
       pass
    assert os.path.exists(temp_env) == False


def test_non_prefix_capable_package():
    """
    Test a package that is not able to be installed with --prefix is proper handled
    """
    pytest_enable_socket()

    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "non_prefix_capable")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "non_prefix_capable"])
    try:
       shutil.rmtree(temp_env)
    except Exception:
       pass

    ## Test a good install into a designated prefix
    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "non_prefix_capable"])

    ## Test a package that is not set up to be installed with the --prefix flag
    args = Namespace(channel='genomics', command='install', debug=False, name=["danrer10-gtf-ensembl-v1"], file=[] ,prefix=temp_env, id = None)
    with pytest.raises(AssertionError) as pytest_wrapped_e:
       install.install((), args)
    assert pytest_wrapped_e.match(":ggd:install: !!ERROR!! the --prefix flag was set but the 'danrer10-gtf-ensembl-v1' data package is not set up to be installed into a different prefix. GGD is unable to fulfill the install request. Remove the --prefix flag to install this data package. Notify the ggd team if you would like this recipe to be updated for --prefix install compatibility")

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "non_prefix_capable"])
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

    ## Test empty name and file parametres
    args = Namespace(channel='genomics', command='install', debug=False, name=[], file=[] ,prefix=None, id = None)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
       install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match(":ggd:install: !!ERROR!! Either a data package name or a file name with --file is required. Neither option was provided.") ## Check that the exit code is 1

    ## Test bad --file  parametres
    args = Namespace(channel='genomics', command='install', debug=False, name=[], file=["FaKe_FilE.Txt"] ,prefix=None, id = None)

    try:
       install.install((), args)
       assert False
    except AssertionError as e:
       assert ":ggd:install: !!ERROR!! The FaKe_FilE.Txt file provided does not exists" in str(e)
    except Exception as e:
       print(str(e))
       assert False

    ## Test a non ggd recipe
    ggd_recipe1 = "Fake-hg19-gaps"
    args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_recipe1], file=[] ,prefix=None, id = None)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
       install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 

    ## Install pfam
    ggd_recipe = "hg19-pfam-domains-ucsc-v1"
    args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_recipe], file=[], prefix=None, id = None)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
       install.install((), args)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: hg19-pfam-domains-ucsc-v1 version 1 is not installed on your system" in output
    assert ":ggd:install: hg19-pfam-domains-ucsc-v1 has not been installed by conda" in output
    assert ":ggd:install: The hg19-pfam-domains-ucsc-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
    assert ":ggd:install:   Attempting to install the following cached package(s):\n\thg19-pfam-domains-ucsc-v1" in output
    assert ":ggd:utils:bypass: Installing hg19-pfam-domains-ucsc-v1 from the ggd-genomics conda channel" in output
    assert ":ggd:install: Updating installed package list" in output
    assert ":ggd:install: Install Complete" in output
    assert ":ggd:install: Installed file locations" in output
    assert ":ggd:install: Environment Variables" in output

    ## Test an already installed ggd recipe
    args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_recipe], file=[], prefix=None, id = None)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
       install.install((), args)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: 'hg19-pfam-domains-ucsc-v1' is already installed." in output
    assert "You can find hg19-pfam-domains-ucsc-v1 here:" in output
    assert ":ggd:install: hg19-pfam-domains-ucsc-v1 version 1 is not installed on your system" not in output

    ## Test a previously installed recipe, but the recipe path is broken 
    ggd_recipe = "hg19-pfam-domains-ucsc-v1"
    args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_recipe], file=[], prefix=None, id = None)

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


def test_install_main_function_multiple_recipes():
    """
    Test main function with mutliple recipe requests
    """

    pytest_enable_socket()

    remove_pfam()

    CONDA_ROOT = utils.conda_root()

    ## Test install with mutliple packages
    recipes = ["grch37-chromsizes-ggd-v1","hg19-chromsizes-ggd-v1"]
    args = Namespace(channel='genomics', command='install', debug=False, name=recipes, file=[], prefix=None, id = None)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
       install.install((), args)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: grch37-chromsizes-ggd-v1 version 1 is not installed on your system" in output
    assert ":ggd:install: grch37-chromsizes-ggd-v1 has not been installed by conda" in output
    assert ":ggd:install: The grch37-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
    assert ":ggd:install: hg19-chromsizes-ggd-v1 version 1 is not installed on your system" in output
    assert ":ggd:install: hg19-chromsizes-ggd-v1 has not been installed by conda" in output
    assert ":ggd:install: The hg19-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
    assert ":ggd:install:   Attempting to install the following cached package(s):\n\tgrch37-chromsizes-ggd-v1\n\thg19-chromsizes-ggd-v1" in output
    assert ":ggd:utils:bypass: Installing grch37-chromsizes-ggd-v1, hg19-chromsizes-ggd-v1 from the ggd-genomics conda channel" in output
    assert ":ggd:install: Updating installed package list" in output
    assert ":ggd:install: Install Complete" in output
    assert ":ggd:install: Installed file locations" in output
    assert ":ggd:install: Environment Variables" in output

    for name in recipes:
       jdict = install.check_ggd_recipe(name,"genomics")
       species = jdict["packages"][name]["identifiers"]["species"]
       build = jdict["packages"][name]["identifiers"]["genome-build"]
       version = jdict["packages"][name]["version"]
       file1 = "{}.txt".format(name)
       assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version))
       assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file1))

    for name in recipes:
       try:
           args = Namespace(channel='genomics', command='uninstall', names=[name])
           uninstall.uninstall((),args)
       except:
           pass


    ## Test install with mutliple packages with --files
    recipes = ["grch38-chromsizes-ggd-v1","hg38-chromsizes-ggd-v1"]
    args = Namespace(channel='genomics', command='install', debug=False, name=[], file=recipes, prefix=None, id = None)

    ## Catch bad file 
    try:
       install.install((),args)
       assert False
    except AssertionError as e:
       assert ":ggd:install: !!ERROR!! The grch38-chromsizes-ggd-v1 file provided does not exists" in str(e)
    except Exception:
       assert False

    ### Create install file 
    install_file = CreateRecipe(
    """
    install_path:
       install.txt: |
           grch38-chromsizes-ggd-v1
           hg38-chromsizes-ggd-v1
    """, from_string=True)

    install_file.write_recipes()
    install_file_dir_path = install_file.recipe_dirs["install_path"]   
    install_file_path = os.path.join(install_file_dir_path,"install.txt")
    args = Namespace(channel='genomics', command='install', debug=False, name=[], file=[install_file_path], prefix=None, id = None)
    ## Try good file
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
       install.install((), args)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: grch38-chromsizes-ggd-v1 version 1 is not installed on your system" in output
    assert ":ggd:install: grch38-chromsizes-ggd-v1 has not been installed by conda" in output
    assert ":ggd:install: The grch38-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
    assert ":ggd:install: hg38-chromsizes-ggd-v1 version 1 is not installed on your system" in output
    assert ":ggd:install: hg38-chromsizes-ggd-v1 has not been installed by conda" in output
    assert ":ggd:install: The hg38-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
    assert ":ggd:install:   Attempting to install the following cached package(s):\n\tgrch38-chromsizes-ggd-v1\n\thg38-chromsizes-ggd-v1" in output
    assert ":ggd:utils:bypass: Installing grch38-chromsizes-ggd-v1, hg38-chromsizes-ggd-v1 from the ggd-genomics conda channel" in output
    assert ":ggd:install: Updating installed package list" in output
    assert ":ggd:install: Install Complete" in output
    assert ":ggd:install: Installed file locations" in output
    assert ":ggd:install: Environment Variables" in output

    for name in recipes:
       jdict = install.check_ggd_recipe(name,"genomics")
       species = jdict["packages"][name]["identifiers"]["species"]
       build = jdict["packages"][name]["identifiers"]["genome-build"]
       version = jdict["packages"][name]["version"]
       file1 = "{}.txt".format(name)
       assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version))
       assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file1))

    for name in recipes:
       try:
           args = Namespace(channel='genomics', command='uninstall', names=[name])
           uninstall.uninstall((),args)
       except:
           pass

## Reduce test time
##    ## Test install with multiple files
##    install_file2 = CreateRecipe(
##    """
##    install_path2:
##        install2.txt: |
##            grch37-chromsizes-ggd-v1
##        
##        install3.txt: |
##            hg19-chromsizes-ggd-v1
##    """, from_string=True)
##    install_file2.write_recipes()
##    install_file2_dir_path = install_file2.recipe_dirs["install_path2"]   
##    install_file2_path = os.path.join(install_file2_dir_path,"install2.txt")
##    install_file3_path = os.path.join(install_file2_dir_path,"install3.txt")
##    args = Namespace(channel='genomics', command='install', debug=False, name=[], file=[install_file2_path,install_file3_path], prefix=None)
##    ## Try good file
##    temp_stdout = StringIO()
##    with redirect_stdout(temp_stdout):
##        install.install((), args)
##    output = temp_stdout.getvalue().strip() 
##    assert ":ggd:install: grch37-chromsizes-ggd-v1 version 1 is not installed on your system" in output
##    assert ":ggd:install: grch37-chromsizes-ggd-v1 has not been installed by conda" in output
##    assert ":ggd:install: The grch37-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
##    assert ":ggd:install: hg19-chromsizes-ggd-v1 version 1 is not installed on your system" in output
##    assert ":ggd:install: hg19-chromsizes-ggd-v1 has not been installed by conda" in output
##    assert ":ggd:install: The hg19-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
##    assert ":ggd:install:   Attempting to install the following cached package(s):\n\tgrch37-chromsizes-ggd-v1\n\thg19-chromsizes-ggd-v1" in output
##    assert ":ggd:utils:bypass: Installing grch37-chromsizes-ggd-v1, hg19-chromsizes-ggd-v1 from the ggd-genomics conda channel" in output
##    assert ":ggd:install: Updating installed package list" in output
##    assert ":ggd:install: Install Complete" in output
##    assert ":ggd:install: Installed file locations" in output
##    assert ":ggd:install: Environment Variables" in output
##
##    for name in ["grch37-chromsizes-ggd-v1","hg19-chromsizes-ggd-v1"]:
##        jdict = install.check_ggd_recipe(name,"genomics")
##        species = jdict["packages"][name]["identifiers"]["species"]
##        build = jdict["packages"][name]["identifiers"]["genome-build"]
##        version = jdict["packages"][name]["version"]
##        file1 = "{}.txt".format(name)
##        assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version))
##        assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file1))
##    for name in ["grch37-chromsizes-ggd-v1","hg19-chromsizes-ggd-v1","grch38-chromsizes-ggd-v1","hg38-chromsizes-ggd-v1"]:
##        try:
##            args = Namespace(channel='genomics', command='uninstall', names=[name])
##            uninstall.uninstall((),args)
##        except:
##            pass
##
##
##    ## Test install with mutliple packages with positional arguments and --files
##    recipes = ["grch37-chromsizes-ggd-v1","hg19-chromsizes-ggd-v1"]
##    args = Namespace(channel='genomics', command='install', debug=False, name=recipes, file=[install_file_path], prefix=None)
##    temp_stdout = StringIO()
##    with redirect_stdout(temp_stdout):
##        install.install((), args)
##    output = temp_stdout.getvalue().strip() 
##    assert ":ggd:install: grch37-chromsizes-ggd-v1 version 1 is not installed on your system" in output
##    assert ":ggd:install: grch37-chromsizes-ggd-v1 has not been installed by conda" in output
##    assert ":ggd:install: The grch37-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
##    assert ":ggd:install: hg19-chromsizes-ggd-v1 version 1 is not installed on your system" in output
##    assert ":ggd:install: hg19-chromsizes-ggd-v1 has not been installed by conda" in output
##    assert ":ggd:install: The hg19-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
##    assert ":ggd:install: grch38-chromsizes-ggd-v1 version 1 is not installed on your system" in output
##    assert ":ggd:install: grch38-chromsizes-ggd-v1 has not been installed by conda" in output
##    assert ":ggd:install: The grch38-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
##    assert ":ggd:install: hg38-chromsizes-ggd-v1 version 1 is not installed on your system" in output
##    assert ":ggd:install: hg38-chromsizes-ggd-v1 has not been installed by conda" in output
##    assert ":ggd:install: The hg38-chromsizes-ggd-v1 package is uploaded to an aws S3 bucket. To reduce processing time the package will be downloaded from an aws S3 bucket" in output
##    assert ":ggd:install:   Attempting to install the following cached package(s):\n\tgrch37-chromsizes-ggd-v1\n\tgrch38-chromsizes-ggd-v1\n\thg19-chromsizes-ggd-v1\n\thg38-chromsizes-ggd-v1" in output
##    assert ":ggd:utils:bypass: Installing grch37-chromsizes-ggd-v1, grch38-chromsizes-ggd-v1, hg19-chromsizes-ggd-v1, hg38-chromsizes-ggd-v1 from the ggd-genomics conda channel" in output
##    assert ":ggd:install: Updating installed package list" in output
##    assert ":ggd:install: Install Complete" in output
##    assert ":ggd:install: Installed file locations" in output
##    assert ":ggd:install: Environment Variables" in output
##
##    for name in ["grch37-chromsizes-ggd-v1","hg19-chromsizes-ggd-v1","grch38-chromsizes-ggd-v1","hg38-chromsizes-ggd-v1"]:
##        jdict = install.check_ggd_recipe(name,"genomics")
##        species = jdict["packages"][name]["identifiers"]["species"]
##        build = jdict["packages"][name]["identifiers"]["genome-build"]
##        version = jdict["packages"][name]["version"]
##        file1 = "{}.txt".format(name)
##        assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version))
##        assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,file1))
##
##    for name in ["grch37-chromsizes-ggd-v1","hg19-chromsizes-ggd-v1","grch38-chromsizes-ggd-v1","hg38-chromsizes-ggd-v1"]:
##        try:
##            args = Namespace(channel='genomics', command='uninstall', names=[name])
##            uninstall.uninstall((),args)
##        except:
##            pass


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
    args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_recipe], file=[], prefix=temp_env, id = None)

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

    
    ## Test using environment short name
    ### Temp conda environment 
    env_name = "temp_env_with_name"
    temp_env = os.path.join(utils.conda_root(), "envs", env_name)
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass

    ## Test a good install into a designated prefix
    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", env_name])

    ## Install
    ggd_recipe = "hg19-pfam-domains-ucsc-v1"
    ggd_channel="genomics"
    jdict = install.check_ggd_recipe(ggd_recipe,ggd_channel)
    species = jdict["packages"][ggd_recipe]["identifiers"]["species"]
    build = jdict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_recipe]["version"]

    args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_recipe], file=[], prefix=env_name, id = None)
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
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


def test_install_meta_recipe():

    pytest_enable_socket()
    import tarfile 
    import tempfile
    from ggd import check_recipe

    tmpdir = tempfile.mkdtemp()

    recipe_path = os.path.join(tmpdir,"meta-recipe-geo-accession-geo-v1")
    os.mkdir(recipe_path)

    ## Download files
    try:
        ## checkusm
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/checksums_file.txt",
                         "--directory-prefix",
                         recipe_path])
        ##  meta.yaml
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/meta.yaml",
                         "--directory-prefix",
                         recipe_path])
        ##  metarecipe.sh
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/metarecipe.sh",
                         "--directory-prefix",
                         recipe_path])
        ## head parser
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/parse_geo_header.py",
                         "--directory-prefix",
                         recipe_path])
        ## Post link
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/post-link.sh", 
                         "--directory-prefix",
                         recipe_path])
        ## recipe.sh
        sp.check_call(["wget", 
                         "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/recipes/genomics/meta-recipe/meta-recipe/meta-recipe-geo-accession-geo-v1/recipe.sh",
                         "--directory-prefix",
                         recipe_path])

    except sp.CalledProcessError as e:
        print(str(e))
        assert False

    ## Original yaml
    orig_yaml = yaml.safe_load(open(os.path.join(recipe_path, "meta.yaml")))
    tarball_file_path = check_recipe._build(recipe_path,orig_yaml)
    assert os.path.isfile(tarball_file_path)

    ## Test install good install with meta-recipe
    recipes = ["meta-recipe-geo-accession-geo-v1"]
    args = Namespace(channel='genomics', command='install', debug=False, name=recipes, file=[], prefix=None, id = "GSE123")

    ## Test install with a meta-recipe but no id
    assert install.install((), args)

    ## Check for update in the ecipe and yaml files
    recipe_contents = ""
    yaml_dict = {}
    with tarfile.open(os.path.join(utils.conda_root(),"pkgs",os.path.basename(tarball_file_path.replace("meta-recipe-geo-accession-geo-v1","gse123-geo-v1"))), mode="r|bz2") as tf:
        for info in tf:
            if info.name == "info/recipe/recipe.sh":
                recipe_contents = tf.extractfile(info)
                recipe_contents = recipe_contents.read().decode()

            elif info.name == "info/recipe/meta.yaml.template":
                yaml_dict = tf.extractfile(info)
                yaml_dict = yaml.safe_load(yaml_dict.read().decode())

    ## Check the recipe contents
    assert recipe_contents == (
"""
curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/soft/GSE123_family.soft.gz" -O -J --silent

curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/matrix/GSE123_series_matrix.txt.gz" -O -J --silent

curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/suppl/GSE123_RAW.tar" -O -J --silent

tar -xf GSE123_RAW.tar
""")
    
    ## check the yaml file
    assert yaml_dict["build"]["noarch"] == orig_yaml["build"]["noarch"] 
    assert yaml_dict["build"]["number"] == orig_yaml["build"]["number"] 
    assert yaml_dict["package"]["name"] != orig_yaml["package"]["name"] 
    assert yaml_dict["package"]["name"] == "gse123-geo-v1"
    assert yaml_dict["package"]["version"] == orig_yaml["package"]["version"] 
    assert yaml_dict["about"]["identifiers"]["genome-build"] == orig_yaml["about"]["identifiers"]["genome-build"] 
    assert yaml_dict["about"]["identifiers"]["species"] == orig_yaml["about"]["identifiers"]["species"]
    assert "updated-species" in yaml_dict["about"]["identifiers"]
    assert yaml_dict["about"]["identifiers"]["updated-species"] == "Mus musculus"
    assert "parent-meta-recipe" in yaml_dict["about"]["identifiers"]
    assert yaml_dict["about"]["identifiers"]["parent-meta-recipe"] == "meta-recipe-geo-accession-geo-v1"
    assert yaml_dict["about"]["keywords"] != orig_yaml["about"]["keywords"] 
    assert yaml_dict["about"]["summary"] != orig_yaml["about"]["summary"] 
    assert yaml_dict["about"]["tags"]["data-provider"] == orig_yaml["about"]["tags"]["data-provider"] 
    assert yaml_dict["about"]["tags"]["data-version"] != orig_yaml["about"]["tags"]["data-version"] 
    assert yaml_dict["about"]["tags"]["genomic-coordinate-base"] == orig_yaml["about"]["tags"]["genomic-coordinate-base"] 

    ## Check the installed files
    species = "meta-recipe"
    build = "meta-recipe"
    name = "gse123-geo-v1"
    version = "1"
    assert os.path.exists(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_family.soft.gz"))
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_series_matrix.txt.gz")) ## From TAR file
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSM3227_jzo026-rp1-v5-u74av2.CEL.gz")) ## From TAR file
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSM3225_jzo016-rp1-v5-u74av2.CEL.gz")) ## From TAR file
    assert not os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_RAW.tar")) ## Tar file should not exists after install it 

    ## Check that the file is in ggd list
    from ggd import list_installed_pkgs

    args = Namespace(command='list', pattern="gse123-geo-v1", prefix=None, reset=False)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_installed_packages((), args)
    output = temp_stdout.getvalue().strip() 
    assert "gse123-geo-v1" in output

    ## test the it can be uninstalled
    try:
        sp.check_call(["ggd", "uninstall", "gse123-geo-v1"])
    except subprocess.CalledProcessError as e:
        print(str(e))
        assert False


    ## Temp different conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_geo_meta_recipe")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_geo_meta_recipe"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass

    ###  Create the temp environment
    sp.check_output(["conda", "create", "--name", "temp_geo_meta_recipe"])

    recipes = ["meta-recipe-geo-accession-geo-v1"]
    args = Namespace(channel='genomics', command='install', debug=False, name=recipes, file=[], prefix=temp_env, id = "GSE123")

    ## Test install with a meta-recipe but no id
    assert install.install((), args)

    ## Check for update in the ecipe and yaml files
    recipe_contents = ""
    yaml_dict = {}
    with tarfile.open(os.path.join(temp_env,"pkgs",os.path.basename(tarball_file_path.replace("meta-recipe-geo-accession-geo-v1","gse123-geo-v1"))), mode="r|bz2") as tf:
        for info in tf:
            if info.name == "info/recipe/recipe.sh":
                recipe_contents = tf.extractfile(info)
                recipe_contents = recipe_contents.read().decode()

            elif info.name == "info/recipe/meta.yaml.template":
                yaml_dict = tf.extractfile(info)
                yaml_dict = yaml.safe_load(yaml_dict.read().decode())

    ## Check the recipe contents
    assert recipe_contents == (
"""
curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/soft/GSE123_family.soft.gz" -O -J --silent

curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/matrix/GSE123_series_matrix.txt.gz" -O -J --silent

curl "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/suppl/GSE123_RAW.tar" -O -J --silent

tar -xf GSE123_RAW.tar
""")
    
    ## check the yaml file
    assert yaml_dict["build"]["noarch"] == orig_yaml["build"]["noarch"] 
    assert yaml_dict["build"]["number"] == orig_yaml["build"]["number"] 
    assert yaml_dict["package"]["name"] != orig_yaml["package"]["name"] 
    assert yaml_dict["package"]["name"] == "gse123-geo-v1"
    assert yaml_dict["package"]["version"] == orig_yaml["package"]["version"] 
    assert yaml_dict["about"]["identifiers"]["genome-build"] == orig_yaml["about"]["identifiers"]["genome-build"] 
    assert yaml_dict["about"]["identifiers"]["species"] == orig_yaml["about"]["identifiers"]["species"]
    assert "updated-species" in yaml_dict["about"]["identifiers"]
    assert yaml_dict["about"]["identifiers"]["updated-species"] == "Mus musculus"
    assert "parent-meta-recipe" in yaml_dict["about"]["identifiers"]
    assert yaml_dict["about"]["identifiers"]["parent-meta-recipe"] == "meta-recipe-geo-accession-geo-v1"
    assert yaml_dict["about"]["keywords"] != orig_yaml["about"]["keywords"] 
    assert yaml_dict["about"]["summary"] != orig_yaml["about"]["summary"] 
    assert yaml_dict["about"]["tags"]["data-provider"] == orig_yaml["about"]["tags"]["data-provider"] 
    assert yaml_dict["about"]["tags"]["data-version"] != orig_yaml["about"]["tags"]["data-version"] 
    assert yaml_dict["about"]["tags"]["genomic-coordinate-base"] == orig_yaml["about"]["tags"]["genomic-coordinate-base"] 

    ## Check the installed files
    species = "meta-recipe"
    build = "meta-recipe"
    name = "gse123-geo-v1"
    version = "1"
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,name,version))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSE123_family.soft.gz"))
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSE123_series_matrix.txt.gz")) ## From TAR file
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSM3227_jzo026-rp1-v5-u74av2.CEL.gz")) ## From TAR file
    assert os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSM3225_jzo016-rp1-v5-u74av2.CEL.gz")) ## From TAR file
    assert not os.path.isfile(os.path.join(temp_env,"share","ggd",species,build,name,version,"GSE123_RAW.tar")) ## Tar file should not exists after install it 

    ## recipe should not be isntalled in the current environmnet
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_family.soft.gz")) == False
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSE123_series_matrix.txt.gz")) == False## From TAR file
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSM3227_jzo026-rp1-v5-u74av2.CEL.gz")) == False  ## From TAR file
    assert os.path.isfile(os.path.join(utils.conda_root(),"share","ggd",species,build,name,version,"GSM3225_jzo016-rp1-v5-u74av2.CEL.gz")) == False ## From TAR file

    ## Check that the file is in ggd list
    from ggd import list_installed_pkgs

    args = Namespace(command='list', pattern="gse123-geo-v1", prefix=temp_env, reset=False)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_installed_packages((), args)
    output = temp_stdout.getvalue().strip() 
    assert "gse123-geo-v1" in output

    ### Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_geo_meta_recipe"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


    ## Test install without 
    recipes = ["meta-recipe-geo-accession-geo-v1"]
    args = Namespace(channel='genomics', command='install', debug=False, name=recipes, file=[], prefix=None, id = None)

    ## Test install with a meta-recipe but no id
    temp_stdout = StringIO()
    with pytest.raises(SystemExit) as pytest_wrapped_e, redirect_stdout(temp_stdout):
        install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: {} is a meta-recipe. Checking meta-recipe for installation".format("meta-recipe-geo-accession-geo-v1") in output
    assert ":ggd:install: An ID is required in order to install a GGD meta-recipe. Please add the '--id <Some ID>' flag and try again" in output


    ## Test install with mutliple packages
    recipes = ["grch37-chromsizes-ggd-v1","meta-recipe-geo-accession-geo-v1"]
    args = Namespace(channel='genomics', command='install', debug=False, name=recipes, file=[], prefix=None, id = "GSE123")

    ## Test install with a meta-recipe but no id
    temp_stdout = StringIO()
    with pytest.raises(SystemExit) as pytest_wrapped_e, redirect_stdout(temp_stdout):
        install.install((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:install: Looking for grch37-chromsizes-ggd-v1 in the 'ggd-genomics' channel" in output
    assert ":ggd:install: grch37-chromsizes-ggd-v1 version 1 is not installed on your system" in output
    assert ":ggd:install: grch37-chromsizes-ggd-v1 has not been installed by conda" in output
    assert ":ggd:install: Looking for meta-recipe-geo-accession-geo-v1 in the 'ggd-genomics' channel" in output
    assert ":ggd:install: meta-recipe-geo-accession-geo-v1 exists in the ggd-genomics channel" in output
    assert ":ggd:install: meta-recipe-geo-accession-geo-v1 is a meta-recipe. Checking meta-recipe for installation" in output
    assert ":ggd:install: GGD is currently only able to install a single meta-recipe at a time. Please remove other pkgs and install them with a subsequent command" in output


    ## Remove tmp dir
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)
