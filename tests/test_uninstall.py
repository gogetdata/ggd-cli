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
from helpers import install_hg19_gaps_v1, uninstall_hg19_gaps_v1, CreateRecipe
from ggd import utils
from ggd import uninstall

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO


#---------------------------------------------------------------------------------------------------------
## Test Label
#---------------------------------------------------------------------------------------------------------

TEST_LABEL = "ggd-uninstall-test"


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
## Unit Tests for ggd uninstall
#---------------------------------------------------------------------------------------------------------

def test_get_channeldata():
    """
    Test the get_channeldata method properly finds a good ggd package and handles a bad ggd package 
    """
    ## Uninstall hg19-gaps-v1
    try:
        uninstall_hg19_gaps_v1()
    except:
        pass

    ## Install hg19-gaps-v1
    try:
        install_hg19_gaps_v1()
    except:
        pass
    
    ## Test normal run
    ggd_recipe = "hg19-gaps-v1"
    ggd_channel = "genomics"
    jdict = uninstall.get_channeldata(ggd_recipe,ggd_channel)
    assert ggd_recipe in jdict["packages"].keys()

    ## Similar installed package
    ggd_recipe = "hg19-gaps"
    ggd_channel = "genomics"
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        uninstall.get_channeldata(ggd_recipe,ggd_channel)
    output = temp_stdout.getvalue().strip() 
    assert "Packages installed on your system that are similar include:" in output
    assert "hg19-gaps-v1" in output
    assert uninstall.get_channeldata(ggd_recipe,ggd_channel) == False

    ## Test bad recipe 
    bad_recipe = "BadRecipe"
    ggd_channel = "genomics"
    with redirect_stdout(temp_stdout):
        uninstall.get_channeldata(bad_recipe,ggd_channel)
    output = temp_stdout.getvalue().strip() 
    assert "Packages installed on your system that are similar include:" in output
    assert "{} is not in the ggd-{} channel".format(bad_recipe,ggd_channel)
    assert "Unable to find any package similar to the package entered. Use 'ggd search' or 'conda find' to identify the right package" in output
    assert "This package may not be installed on your system" in output
    assert uninstall.get_channeldata(bad_recipe,ggd_channel) == False

    ## Test bad channel 
    ggd_recipe = "hg19-gaps-v1"
    bad_channel = "BadChannel"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        uninstall.get_channeldata(ggd_recipe,bad_channel) ## Exit due to bad url from ggd.search
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1

def test_get_similar_pkg_installed_by_conda():
    """
    Test the get_similar_pkg_installed_by_conda function 
    """

    ## Test a non similar package name
    not_installed = "Not_an_installed_package"
    assert uninstall.get_similar_pkg_installed_by_conda(not_installed) == ""

    
    installed_requirement = "request"
    output = uninstall.get_similar_pkg_installed_by_conda(installed_requirement)
    assert "requests" in output
    assert "pyyaml" not in output

    installed_requirement = "yaml"
    output = uninstall.get_similar_pkg_installed_by_conda(installed_requirement)
    assert "pyyaml" in output
    assert "oyaml" in output
    assert "requests" not in output
    
    ## Make sure hg19-gaps-v1 is installed
    install_hg19_gaps_v1()
    ggd_recipe = "hg19-gaps"
    output = uninstall.get_similar_pkg_installed_by_conda(ggd_recipe)
    assert "hg19-gaps-v1" in output
    

def test_check_conda_installation():
    """
    Test the check_conda_installation function. Test if conda can properly remove the installed ggd package if it is installed
    """

    ## Test that the function properly handles not installed 
    ggd_recipe = "grch37-reference-genome-v1"
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        uninstall.check_conda_installation(ggd_recipe)
    output = temp_stdout.getvalue().strip() 
    assert "{} is NOT installed on your system".format(ggd_recipe) in output


    ## Test that a similar package name that is not installed is handled correctly 
    ggd_recipe = "hg19-gaps"
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        uninstall.check_conda_installation(ggd_recipe)
    output = temp_stdout.getvalue().strip() 
    assert "{} is NOT installed on your system".format(ggd_recipe) in output


    ## test conda correctly uninstalls the hg19-gaps-v1 package previously installed
    ggd_recipe = "hg19-gaps-v1"
    assert uninstall.check_conda_installation(ggd_recipe) == 0
    output = sp.check_output(["conda", "list", ggd_recipe]).decode('utf8')
    assert ggd_recipe not in output


def test_conda_uninstall():
    """
    Test the conda_uninstall function to properly uninstall a ggd package using conda
    """
    ## Uninstall hg19-gaps-v1
    try:
        uninstall_hg19_gaps_v1()
    except:
        pass

    ## Install hg19-gaps-v1
    try:
        install_hg19_gaps_v1()
    except:
        pass

    ## uninstall hg19-gaps-v1
    ggd_recipe = "hg19-gaps-v1"
    assert uninstall.conda_uninstall(ggd_recipe) == 0
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        uninstall.check_conda_installation(ggd_recipe)
    output = temp_stdout.getvalue().strip() 
    assert "{} is NOT installed on your system".format(ggd_recipe) in output

    ## Test a bad install
    ggd_recipe = "Not_A_Real_GGD_Recipe"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        uninstall.conda_uninstall(ggd_recipe)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1
    

def test_check_for_installation():
    """
    Test the check_for_installation function to check if the ggd package is installed using the ggd file handling information
    """
    ## Test a not installed ggd recipe 
    ggd_recipe = "grch37-reference-genome-v1"
    ggd_channel = "genomics"
    jdict = uninstall.get_channeldata(ggd_recipe,ggd_channel)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        uninstall.check_for_installation(ggd_recipe,jdict)
    output = temp_stdout.getvalue().strip() 
    assert "{} is not in the ggd recipe storage".format(ggd_recipe) in output

    ## Test installed package
    ggd_recipe = "hg19-gaps-v1"
    ggd_channel = "genomics"
    jdict = uninstall.get_channeldata(ggd_recipe,ggd_channel)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        uninstall.check_for_installation(ggd_recipe,jdict)
    output = temp_stdout.getvalue().strip() 
    assert "Removing {} version {} file(s) from ggd recipe storage".format(ggd_recipe,jdict["packages"][ggd_recipe]["version"]) in output


def test_remove_from_condaroot():
    """
    Test that the remove_from_condaroot function properly removes installed ggd packages from the conda root
    """

    ## install hg19-gaps-v1
    install_hg19_gaps_v1()

    ggd_recipe = "hg19-gaps-v1"
    ggd_channel = "genomics"
    version = uninstall.get_channeldata(ggd_recipe,ggd_channel)["packages"][ggd_recipe]["version"]

    ## Check that the files are in the conda root
    conda_root = utils.conda_root()
    check_list = sp.check_output(['find', conda_root, '-name', ggd_recipe+"-"+str(version)+"*"]).decode('utf8').strip().split("\n")
    for f in check_list:
        if conda_root in f:
            if conda_root+"/envs/" not in f:
                assert ggd_recipe+"-"+str(version) in f 
    
    ## remove ggd recipe files from conda root
    uninstall.remove_from_condaroot(ggd_recipe,version)

    ## Check that the files were removed
    conda_root = utils.conda_root()
    check_list = str(sp.check_output(["find", conda_root, "-name", ggd_recipe+"-"+str(version)+"*"], shell=True)).strip().split("\n")
    for f in check_list:
        if conda_root in f:
            if conda_root+"/envs/" not in f:
                assert ggd_recipe+"-"+str(version) not in f 

       
    ## Finish uninstalling hg19-gaps-v1
    uninstall_hg19_gaps_v1()


def test_uninstall():
    """
    Test that a package is properly uninstalled using the main uninstall funciton
    """

    ## Test handling of a package not installed
    ggd_recipe = "not-a-real-recipe"
    args = Namespace(channel='genomics', command='uninstall', name=ggd_recipe)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        uninstall.uninstall((),args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is ""


    ## Test a good uninstall
    #### Install hg19-gaps-v1
    install_hg19_gaps_v1()

    #### Check non-failure uninstall command
    ggd_recipe = "hg19-gaps-v1"
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

