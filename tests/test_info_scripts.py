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
from helpers import install_hg19_gaps_ucsc_v1, uninstall_hg19_gaps_ucsc_v1, CreateRecipe
from ggd import show_env
from ggd import list_files
from ggd import list_pkg_info
from ggd import list_installed_pkgs
from ggd import predict_path
from ggd import utils
from ggd import install
from ggd import uninstall
from ggd.utils import get_conda_package_list 

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO

#---------------------------------------------------------------------------------------------------------
## enable socket
#---------------------------------------------------------------------------------------------------------
from pytest_socket import disable_socket, enable_socket

def pytest_enable_socket():
    enable_socket()

def pytest_disable_socket():
    disable_socket()

#---------------------------------------------------------------------------------------------------------
## Test Label
#---------------------------------------------------------------------------------------------------------

TEST_LABEL = "ggd-info-scripts-test"


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


#-----------------------------------------------------------------------------------------------------------------------
# Unit Test for ggd show-env, ggd get-files, ggd pkg-info, ggd list, and predict-path
#-----------------------------------------------------------------------------------------------------------------------


#----------------------------------------------------
## Test functions based on hg19-gaps being installed
#----------------------------------------------------


### Show-env

def test_show_env_goodrun():
    """
    Test that show_env functoin properly provides the environment variable for an installed package
    """
    pytest_enable_socket()

    try:
        uninstall_hg19_gaps_ucsc_v1()
    except:
        pass

    try:
        install_hg19_gaps_ucsc_v1()
    except:
        pass

    parser = ()
    args = Namespace(command='show-env', pattern=None)
    dir_env_var_name = "$ggd_hg19_gaps_ucsc_v1_dir"
    file_env_var_name = "$ggd_hg19_gaps_ucsc_v1_file"

    ## Test a normal run
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.show_env(parser,args)
    output = temp_stdout.getvalue().strip() 
    assert (dir_env_var_name in output)
    assert (file_env_var_name in output)

    ## Test active environment variables
    sp.check_call(["activate", "base"])
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.show_env(parser,args)
    output = temp_stdout.getvalue().strip() 
    newout = ""
    active = False
    for line in output.strip().split("\n"):
        if "Active environment variables:" in line:
            active = True
        if "Inactive or out-of-date environment variables:" in line:
            active = False
        if active:
            newout += line
    assert (dir_env_var_name in output)
    assert (file_env_var_name in output)


def test_show_env_with_pattern():
    """
    Test that adding the pattern parameter to show-env properly filters the results
    """
    pytest_enable_socket()


    dir_env_var_name = "$ggd_hg19_gaps_ucsc_v1_dir"
    file_env_var_name = "$ggd_hg19_gaps_ucsc_v1_file"
    parser = ()

    ## Good pattern should have "ggd_hg19_gaps" in the results
    args = Namespace(command='show-env', pattern="gaps")
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.show_env(parser,args)
    output = temp_stdout.getvalue().strip() 
    assert (dir_env_var_name in output)
    assert (file_env_var_name in output)

    ## Bad pattern should return "No matching recipe variables found for this environment"
    args = Namespace(command='show-env', pattern="NONE")
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.show_env(parser,args)
    output = temp_stdout.getvalue().strip() 
    assert (dir_env_var_name not in output)
    assert (file_env_var_name not in output)
    assert ("No matching recipe variables found for this environment" in output)


    ## invalid pattern should exit
    args = Namespace(command='show-env', pattern=")()(")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        show_env.show_env(parser,args) 
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1


def replace_env_var(active_var, deactive_var, active_loc, deactive_loc):
    """
    Helper method for test_remove_env_variables. Replaces environment variable removed 
    """
    pytest_enable_socket()

    with open(active_loc, "a") as a:
        a.write(active_var)
    with open(deactive_loc, "a") as d:
        d.write(deactive_var)
    

def test_remove_env_variable():
    """
    Test that the remove_env_varial correctly removes the env var from the activated.d/env_vars.sh file
    """
    pytest_enable_socket()

    dir_main_env_var = "ggd_hg19_gaps_ucsc_v1_dir"
    file_main_env_var = "ggd_hg19_gaps_ucsc_v1_file"

    conda_root, conda_path = utils.get_conda_env()
    active_env_file = os.path.join(conda_path, "etc", "conda", "activate.d", "env_vars.sh")
    deactive_env_file = os.path.join(conda_path, "etc", "conda", "deactivate.d", "env_vars.sh")

    dir_active_env_var = str([x for x in open(active_env_file, "r") if dir_main_env_var in x][0])
    file_active_env_var = str([x for x in open(active_env_file, "r") if file_main_env_var in x][0])
    dir_deactive_env_var = str([x for x in open(deactive_env_file, "r") if dir_main_env_var in x][0])
    file_deactive_env_var = str([x for x in open(deactive_env_file, "r") if file_main_env_var in x][0])

    ## test that a env variable not in the files does not remove those that are in the files:
    env_var = "ggd_NOT-in-file"
    show_env.remove_env_variable(env_var)

    found = False
    with open(active_env_file, "r") as a:
        for var in a:
            if re.search(r"\b"+dir_main_env_var+"=", var):
                found = True
                break
    assert found == True

    found = False
    with open(active_env_file, "r") as a:
        for var in a:
            if re.search(r"\b"+file_main_env_var+"=", var):
                found = True
                break
    assert found == True
                
    found = False
    with open(deactive_env_file, "r") as d:
        for var in d:
            if re.search(r"\b"+dir_main_env_var+r"\b", var):
                found = True
                break
    assert found == True
        
    found = False
    with open(deactive_env_file, "r") as d:
        for var in d:
            if re.search(r"\b"+file_main_env_var+r"\b", var):
                found = True
                break
    assert found == True

    ## Test a proper removal of a environment variable
    show_env.remove_env_variable(dir_main_env_var)
    found = False
    with open(active_env_file, "r") as a:
        for var in a:
            if re.search(r"\b"+dir_main_env_var+"=", var):
                found = True
                break
    assert found == False

    show_env.remove_env_variable(file_main_env_var)
    found = False
    with open(active_env_file, "r") as a:
        for var in a:
            if re.search(r"\b"+file_main_env_var+"=", var):
                found = True
                break
    assert found == False
    

    found = False
    with open(deactive_env_file, "r") as d:
        for var in d:
            if re.search(r"\b"+dir_main_env_var+r"\b", var):
                found = True
                break
    assert found == False

    found = False
    with open(deactive_env_file, "r") as d:
        for var in d:
            if re.search(r"\b"+file_main_env_var+r"\b", var):
                found = True
                break
    assert found == False

    replace_env_var(dir_active_env_var, dir_deactive_env_var, active_env_file, deactive_env_file)
    replace_env_var(file_active_env_var, file_deactive_env_var, active_env_file, deactive_env_file)

    ## Test that a similar env variable does not remove other env variables
    env_var = "ggd_hg19-ga"

    show_env.remove_env_variable(env_var)
    found = False
    with open(active_env_file, "r") as a:
        for var in a:
            if re.search(r"\b"+dir_main_env_var+"=", var):
                found = True
                break
    assert found == True

    found = False
    with open(active_env_file, "r") as a:
        for var in a:
            if re.search(r"\b"+file_main_env_var+"=", var):
                found = True
                break
    assert found == True

    found = False
    with open(deactive_env_file, "r") as d:
        for var in d:
            if re.search(r"\b"+dir_main_env_var+r"\b", var):
                found = True
                break
    assert found == True

    found = False
    with open(deactive_env_file, "r") as d:
        for var in d:
            if re.search(r"\b"+file_main_env_var+r"\b", var):
                found = True
                break
    assert found == True


def test_remove_env_variable_different_prefix():
    """
    Test that the remove_env_varial correctly removes the env var in non conda_root prefix from the activated.d/env_vars.sh file
    """
    pytest_enable_socket()

    ## Set up temp_env
    env_name = "temp_env12"
    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", env_name)
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    ## Create conda environmnet 
    sp.check_output(["conda", "create", "--name", env_name])

    ## Install ggd recipe using conda into temp_env
    ggd_package = "hg19-pfam-domains-ucsc-v1"
    install_args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_package], file=[], prefix = temp_env, id = None)
    assert install.install((), install_args) == True

    dir_main_env_var = "ggd_hg19_pfam_domains_ucsc_v1_dir"
    file_main_env_var = "ggd_hg19_pfam_domains_ucsc_v1_file"

    conda_root, conda_path = utils.get_conda_env(prefix=temp_env)
    assert conda_path == temp_env

    active_env_file = os.path.join(conda_path, "etc", "conda", "activate.d", "env_vars.sh")
    deactive_env_file = os.path.join(conda_path, "etc", "conda", "deactivate.d", "env_vars.sh")

    dir_active_env_var = str([x for x in open(active_env_file, "r") if dir_main_env_var in x][0])
    file_active_env_var = str([x for x in open(active_env_file, "r") if file_main_env_var in x][0])
    dir_deactive_env_var = str([x for x in open(deactive_env_file, "r") if dir_main_env_var in x][0])
    file_deactive_env_var = str([x for x in open(deactive_env_file, "r") if file_main_env_var in x][0])

    ## Test a proper removal of a environment variable
    show_env.remove_env_variable(dir_main_env_var,prefix=temp_env)
    found = False
    with open(active_env_file, "r") as a:
        for var in a:
            if re.search(r"\b"+dir_main_env_var+"=", var):
                found = True
                break
    assert found == False

    show_env.remove_env_variable(file_main_env_var,prefix=temp_env)
    found = False
    with open(active_env_file, "r") as a:
        for var in a:
            if re.search(r"\b"+file_main_env_var+"=", var):
                found = True
                break
    assert found == False

    found = False
    with open(deactive_env_file, "r") as d:
        for var in d:
            if re.search(r"\b"+dir_main_env_var+r"\b", var):
                found = True
                break
    assert found == False

    found = False
    with open(deactive_env_file, "r") as d:
        for var in d:
            if re.search(r"\b"+file_main_env_var+r"\b", var):
                found = True
                break
    assert found == False

    replace_env_var(dir_active_env_var, dir_deactive_env_var, active_env_file, deactive_env_file)
    replace_env_var(file_active_env_var, file_deactive_env_var, active_env_file, deactive_env_file)

    ## Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


def test_activate_environment_variables():
    """
    Test that the activate_environment_variables function properly activates the environment variables
    """
    pytest_enable_socket()

    dir_env_var_name = "$ggd_hg19_gaps_ucsc_v1_dir"
    file_env_var_name = "$ggd_hg19_gaps_ucsc_v1_file"
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.activate_environment_variables()
    output = temp_stdout.getvalue().strip() 
    newout = ""
    active = False
    for line in output.strip().split("\n"):
        if "Active environment variables:" in line:
            active = True
        if "Inactive or out-of-date environment variables:" in line:
            active = False
        if active:
            newout += line
    assert (dir_env_var_name in output)
    assert (file_env_var_name in output)


def test_test_vars():
    """
    Test that the test_vars function correclty provides the active and inactive environemnt variables
    """
    pytest_enable_socket()

    matching_vars = {'ggd_hg38_gaps_11_mar_2019': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-gaps_11-mar-2019/1', 'ggd_hg38_reference_genome_ucsc': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-reference-genome-ucsc/1', 'ggd_hg38_cpg_islands': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-cpg-islands/1', 'ggd_grch38_reference_genome_ensembl': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/GRCh38/grch38-reference-genome-ensembl/1', 'ggd_hg19_cpg_islands': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg19/hg19-cpg-islands/1', 'ggd_hg19_gaps': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg19/hg19-gaps/1', 'ggd_hg19_reference_genome_ucsc': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg19/hg19-reference-genome-ucsc/1', 'ggd_hg38_simplerepeats': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-simplerepeats/1', 'ggd_hg19_pfam_domains_ucsc': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg19/hg19-pfam-domains-ucsc/1', 'ggd_grch37_esp_variants': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/GRCh37/grch37-esp-variants/1', 'ggd_hg38_pfam_domains_ucsc': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-pfam-domains-ucsc/1'}
    active = [x for x in matching_vars if x in os.environ and os.environ[x] == matching_vars[x]]  
    inactive = [x for x in matching_vars if x not in active]

    active_list, inactive_list = show_env.test_vars(matching_vars)

    for var in active_list:
        assert var in active 

    for var in inactive_list:
        assert var in inactive


### get files

def test_in_ggd_channel():
    """
    Test that the in_ggd_channel from ggd list-files works correctly 
    """
    pytest_enable_socket()

    ## Test that in_ggd_channel properly returns the species, genome-build, and versoin if it is in the channel
    ggd_package = "hg19-gaps-ucsc-v1"
    channel = "genomics"
    species, build, version = list_files.in_ggd_channel([ggd_package], channel, utils.conda_root())
    assert species == "Homo_sapiens"
    assert build == "hg19"
    assert version == "1"
    
    ## test that in_ggd_channel properly handels bad channels 
    ggd_package = "hg19-gaps-ucsc-v1"
    channel = "not_a_real_channel"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.in_ggd_channel([ggd_package], channel, utils.conda_root())
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("The '{c}' channel is not a ggd conda channel".format(c=channel)) ## check that the exit code is 1

    
    ## test that in_ggd_channel properly handels bad recipe name 
    ggd_package = "NOT_A_REAL_PACKAGE_NAME"
    channel = "genomics"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.in_ggd_channel([ggd_package], channel, utils.conda_root())
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("2") ## check that the exit code is 1


def test_list_files():
    """
    Test the main method of list-files 
    """
    pytest_enable_socket()

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

    ##Test that the correct file paths are returned with the patterns key set  key set
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=file1, prefix=None, species=None, version=None)
    
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_files.list_files((),args)
    output = str(temp_stdout.getvalue().strip()) 
    assert re.search(file1+"$", output)
    assert re.search(file2+"$", output) == None
    assert len(output.split("\n")) == 1

    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=file2, prefix=None, species=None, version=None)
    
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_files.list_files((),args)
    output = str(temp_stdout.getvalue().strip()) 
    assert re.search(file1+"$", output) == None
    assert re.search(file2+"$", output)
    assert len(output.split("\n")) == 1

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


def test_list_files_with_prefix():
    """
    test the list-files function with --prefix flag set
    """
    pytest_enable_socket()

    env_name = "temp_e"
    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", env_name)
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    ## Create conda environmnet 
    sp.check_output(["conda", "create", "--name", env_name])

    ## Install ggd recipe using conda into temp_env
    ggd_package = "hg19-pfam-domains-ucsc-v1"
    install_args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_package], file=[], prefix = temp_env, id=None)
    assert install.install((), install_args) == True


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
    jdict = install.check_ggd_recipe(ggd_package,"genomics")
    species = jdict["packages"][ggd_package]["identifiers"]["species"]
    build = jdict["packages"][ggd_package]["identifiers"]["genome-build"]
    version = jdict["packages"][ggd_package]["version"]
    assert os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file1) in output
    assert os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file2) in output
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file1))
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file2))


    ## Test with environment name instead of path
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=None, prefix=env_name, species=None, version=None)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_files.list_files((),args)
    output = str(temp_stdout.getvalue().strip()) 
    assert file1 in  output
    assert file2 in  output
    assert temp_env in output
    assert len(output.split("\n")) == 2
    assert os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file1) in output
    assert os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file2) in output
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file1))
    assert os.path.exists(os.path.join(temp_env,"share","ggd",species,build,ggd_package,version,file2))
    

    ## Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", env_name])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


### pkg-info


def test_check_if_ggd_recipe():
    """
    Test if check_if_ggd_recipe correclty identifies if a ggd recipe is a recipe or not
    """

    pytest_enable_socket()

    ## Test a normal package name and channel
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    assert list_pkg_info.check_if_ggd_recipe(ggd_package, ggd_channel) == True

    ## Test a normal package name but bad channel
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "BAD_CHANNEL"
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        assert list_pkg_info.check_if_ggd_recipe(ggd_package, ggd_channel) == False
    output = temp_stdout.getvalue().strip() 
    assert "The hg19-gaps-ucsc-v1 package is not in the ggd-{c} channel.".format(c=ggd_channel) in output

    ## Test a bad package name and normal channel
    ggd_package = "BAD_Recipe"
    ggd_channel = "genomics"
    assert list_pkg_info.check_if_ggd_recipe(ggd_package, ggd_channel) == False


def test_get_pkg_info():
    """
    Test that get_pkg_info correctly returns the pkg info or handles other problems 
    """

    pytest_enable_socket()

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


def test_get_meta_yaml_info():
    """
    Test the get_meta_yaml_info file to correctly get the correct info
    """
    pytest_enable_socket()


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

        assert "\t\x1b[1mGGD-Package:\x1b[0m fake-recipe" in output
        assert "\t\x1b[1mGGD-Channel:\x1b[0m ggd-genomics" in output
        assert "\t\x1b[1mGGD Pkg Version:\x1b[0m 1" in output
        assert "\t\x1b[1mSummary:\x1b[0m A fake recipe for testing" in output
        assert "\t\x1b[1mSpecies:\x1b[0m Homo_sapiens" in output
        assert "\t\x1b[1mGenome Build:\x1b[0m hg19" in output
        assert "\t\x1b[1mKeywords:\x1b[0m gaps, region" in output
        assert "\t\x1b[1mData Version:\x1b[0m Today" in output
        conda_root = utils.conda_root()
        assert "\t\x1b[1mPkg File Path:\x1b[0m {}/share/ggd/Homo_sapiens/hg19/fake-recipe/1".format(conda_root) in output
        assert "\t\x1b[1mInstalled Pkg Files:\x1b[0m " in output
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


    ## Test get_meta_yaml_info function correctly returns output for a recipe tags

    recipe = CreateRecipe(

        """
        fake-recipe2:
            meta.yaml: |
                build:
                  binary_relocation: false
                  detect_binary_files_with_prefix: false
                  noarch: generic
                  number: 1
                extra:
                  authors: me
                package:
                  name: fake-recipe2
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
                    cached:
                    - uploaded_to_aws
                    data-provider: ME
                    data-version: Today
                    file-type:
                    - something
                    final-files:
                    - fake2.something.gz
                    - fake2.something.gz.tbi
                    genomic-coordinate-base: 0-based-inclusive
                    ggd-channel: fake2 


        """, from_string=True)

    recipe.write_recipes()

    ggd_package = "fake-recipe2"
    ggd_channel = "fake2"
    meta_yaml_file = os.path.join(recipe.recipe_dirs[ggd_package],"meta.yaml")

    try:
        f = open(meta_yaml_file, "r")

        temp_stdout = StringIO()
        with redirect_stdout(temp_stdout):
            list_pkg_info.get_meta_yaml_info(f,ggd_package,ggd_channel)
        output = temp_stdout.getvalue().strip() 
        assert "\t\x1b[1mGGD-Package:\x1b[0m fake-recipe2" in output
        assert "\t\x1b[1mGGD-Channel:\x1b[0m ggd-fake2" in output
        assert "\t\x1b[1mGGD Pkg Version:\x1b[0m 1" in output
        assert "\t\x1b[1mSummary:\x1b[0m A fake recipe for testing" in output
        assert "\t\x1b[1mSpecies:\x1b[0m Homo_sapiens" in output
        assert "\t\x1b[1mGenome Build:\x1b[0m hg19" in output
        assert "\t\x1b[1mKeywords:\x1b[0m gaps, region" in output
        assert "\t\x1b[1mCached:\x1b[0m uploaded_to_aws" in output
        assert "\t\x1b[1mData Provider:\x1b[0m ME" in output
        assert "\t\x1b[1mData Version:\x1b[0m Today" in output
        assert "\t\x1b[1mFile type(s):\x1b[0m something" in output
        assert "\t\x1b[1mData file coordinate base:\x1b[0m 0-based-inclusive" in output
        assert "\t\x1b[1mIncluded Data Files:\x1b[0m " in output
        assert "\t\tfake2.something.gz"  in output
        assert "\t\tfake2.something.gz.tbi" in output
        conda_root = utils.conda_root()
        assert "\t\x1b[1mPkg File Path:\x1b[0m {}/share/ggd/Homo_sapiens/hg19/fake-recipe2/1".format(conda_root) in output 
        assert "\t\x1b[1mInstalled Pkg Files:\x1b[0m " in output
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

    ## Test get_meta_yaml_info function correctly returns output meta-recipe updated meta.yaml files

    recipe = CreateRecipe(

        """
        fake-meta-recipe1:
            meta.yaml: |
                build:
                  binary_relocation: false
                  detect_binary_files_with_prefix: false
                  noarch: generic
                  number: 1
                extra:
                  authors: me
                package:
                  name: fake-meta-recipe1
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
                    parent-meta-recipe: fake-meta-recipe0
                    genome-build: meta-recipe
                    updated-genome-build: UPDATED-meta-recipe
                    species: meta-recipe
                    updated-species: UPDATED-meta-recipe
                  keywords:
                  - gaps
                  - region
                  summary: A fake meta-recipe for testing 
                  tags:
                    data-provider: ME
                    data-version: Today
                    file-type:
                    - something
                    final-files:
                    - fake3.something.gz
                    - fake3.something.gz.tbi
                    genomic-coordinate-base: 0-based-inclusive
                    ggd-channel: fake3 


        """, from_string=True)

    recipe.write_recipes()

    ggd_package = "fake-meta-recipe1"
    ggd_channel = "fake3"
    meta_yaml_file = os.path.join(recipe.recipe_dirs[ggd_package],"meta.yaml")

    try:
        f = open(meta_yaml_file, "r")

        temp_stdout = StringIO()
        with redirect_stdout(temp_stdout):
            list_pkg_info.get_meta_yaml_info(f,ggd_package,ggd_channel)
        output = temp_stdout.getvalue().strip() 
        print("OUTPUT: '''", output, "'''")
        assert "\t\x1b[1mGGD-Package:\x1b[0m fake-meta-recipe1" in output
        assert "\t\x1b[1mGGD Parent Meta-Recipe:\x1b[0m fake-meta-recipe0" in output
        assert "\t\x1b[1mGGD-Channel:\x1b[0m ggd-fake3" in output
        assert "\t\x1b[1mGGD Pkg Version:\x1b[0m 1" in output
        assert "\t\x1b[1mSummary:\x1b[0m A fake meta-recipe for testing" in output
        assert "\t\x1b[1mSpecies:\x1b[0m (Updated) UPDATED-meta-recipe" in output
        assert "\t\x1b[1mGenome Build:\x1b[0m (Updated) UPDATED-meta-recipe" in output
        assert "\t\x1b[1mKeywords:\x1b[0m gaps, region" in output
        assert "\t\x1b[1mCached:\x1b[0m uploaded_to_aws" not in output
        assert "\t\x1b[1mData Provider:\x1b[0m ME" in output
        assert "\t\x1b[1mData Version:\x1b[0m Today" in output
        assert "\t\x1b[1mFile type(s):\x1b[0m something" in output
        assert "\t\x1b[1mData file coordinate base:\x1b[0m 0-based-inclusive" in output
        assert "\t\x1b[1mIncluded Data Files:\x1b[0m " in output
        assert "\t\tfake3.something.gz"  in output
        assert "\t\tfake3.something.gz.tbi" in output
        conda_root = utils.conda_root()
        assert "\t\x1b[1mPkg File Path:\x1b[0m {}/share/ggd/meta-recipe/meta-recipe/fake-meta-recipe1/1".format(conda_root) in output 
        assert "\t\x1b[1mInstalled Pkg Files:\x1b[0m " in output
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
    

def test_print_recipe():
    """
    Test the print_recipe fucntion 
    """
    pytest_enable_socket()

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
    

def test_info_main():
    """
    test the main funtion, info(parser, args), of pkg-info
    """
    pytest_enable_socket()

    ## Normal run
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    args = Namespace(channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=False, prefix = None)
    assert list_pkg_info.info((),args) == True

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.info((),args)
    output = temp_stdout.getvalue().strip() 
    ## Include checks for meta yaml tag keys like final files and approximate file sizes
    assert "\t\x1b[1mGGD-Package:\x1b[0m hg19-gaps-ucsc-v1" in output 
    assert "\t\x1b[1mGGD-Channel:\x1b[0m ggd-genomics" in output
    assert "\t\x1b[1mGGD Pkg Version:\x1b[0m 1" in output
    assert "\t\x1b[1mSummary:\x1b[0m Assembly gaps from UCSC in bed fromat. Scaffoldings that are not contained in the hg19.genome file are removed" in output
    assert "\t\x1b[1mSpecies:\x1b[0m Homo_sapiens" in output
    assert "\t\x1b[1mGenome Build:\x1b[0m hg19" in output
    assert "\t\x1b[1mKeywords:\x1b[0m gaps, regions, gap-locations, Assembly-Gaps, clone-gaps, contig-gaps, centromere-gaps, telomere-gaps, heterochromatin-gaps, short-arm-gaps" in output
    assert "\t\x1b[1mCached:\x1b[0m uploaded_to_aws" in output

    assert "\t\x1b[1mData Provider:\x1b[0m UCSC" in output
    assert "\t\x1b[1mData Version:\x1b[0m 22-Mar-2020" in output
    assert "\t\x1b[1mFile type(s):\x1b[0m bed" in output
    assert "\t\x1b[1mData file coordinate base:\x1b[0m 0-based-inclusive" in output
    assert "\t\x1b[1mIncluded Data Files:\x1b[0m" in output
    assert "\t\x1b[1mApproximate Data File Sizes:\x1b[0m" in output

    conda_root = utils.conda_root()
    assert "\t\x1b[1mPkg File Path:\x1b[0m {}/share/ggd/Homo_sapiens/hg19/hg19-gaps-ucsc-v1/1".format(conda_root) in output 
    assert "\t\x1b[1mInstalled Pkg Files:\x1b[0m " in output
    assert "\t\t{}/share/ggd/Homo_sapiens/hg19/hg19-gaps-ucsc-v1/1/hg19-gaps-ucsc-v1.bed.gz.tbi".format(conda_root) in output
    assert "\t\t{}/share/ggd/Homo_sapiens/hg19/hg19-gaps-ucsc-v1/1/hg19-gaps-ucsc-v1.bed.gz".format(conda_root) in output


    ## Normal run with print recipes 
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    args = Namespace(channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=True, prefix = None)
    assert list_pkg_info.info((),args) == True

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.info((),args)
    output = temp_stdout.getvalue().strip() 
    assert "\t\x1b[1mGGD-Package:\x1b[0m {}".format(ggd_package) in output 
    assert "\t\x1b[1mGGD-Channel:\x1b[0m ggd-{}".format(ggd_channel) in output
    assert "\t\x1b[1mGGD Pkg Version:\x1b[0m 1" in output
    assert "\t\x1b[1mSummary:\x1b[0m Assembly gaps from UCSC in bed fromat. Scaffoldings that are not contained in the hg19.genome file are removed" in output
    assert "\t\x1b[1mSpecies:\x1b[0m Homo_sapiens" in output
    assert "\t\x1b[1mGenome Build:\x1b[0m hg19" in output
    assert "\t\x1b[1mKeywords:\x1b[0m gaps, regions, gap-locations, Assembly-Gaps, clone-gaps, contig-gaps, centromere-gaps, telomere-gaps, heterochromatin-gaps, short-arm-gaps" in output
    assert "\t\x1b[1mCached:\x1b[0m uploaded_to_aws" in output
    assert "{} recipe file:\n***********************".format(ggd_package) in output 


    ## Bad recipe run
    ggd_package = "Bad-recipe"
    ggd_channel = "genomics"
    args = Namespace(channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=False, prefix = None)
    assert list_pkg_info.info((),args) == False

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.info((),args)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:pkg-info: The {} package is not in the ggd-{} channel.".format(ggd_package, ggd_channel) in output 


    ## Bad recipe run with print recipe
    ggd_package = "Bad-recipe"
    ggd_channel = "genomics"
    args = Namespace(channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=True, prefix = None)
    assert list_pkg_info.info((),args) == False

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.info((),args)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:pkg-info: The {} package is not in the ggd-{} channel.".format(ggd_package, ggd_channel) in output 


def test_info_main_in_different_prefix():

    ## Test using a different prefix
    ### Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_pkg_info_env")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_pkg_info_env"])
    try: 
        shutil.rmtree(temp_env)
    except Exception:
        pass 
    ### Create conda environmnet 
    sp.check_output(["conda", "create", "--name", "temp_pkg_info_env"])

    ### Install ggd recipe using conda into temp_env
    ggd_package = "hg19-gaps-ucsc-v1"
    install_args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_package], file=[], prefix = temp_env, id = None)
    assert install.install((), install_args) == True 


    ## Test different prefix 

    ggd_channel = "genomics"
    args = Namespace(channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=False, prefix = temp_env)
    assert list_pkg_info.info((),args) == True

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.info((),args)
    output = temp_stdout.getvalue().strip() 
    ## Include checks for meta yaml tag keys like final files and approximate file sizes
    assert "\t\x1b[1mGGD-Package:\x1b[0m hg19-gaps-ucsc-v1" in output 
    assert "\t\x1b[1mGGD-Channel:\x1b[0m ggd-genomics" in output
    assert "\t\x1b[1mGGD Pkg Version:\x1b[0m 1" in output
    assert "\t\x1b[1mSummary:\x1b[0m Assembly gaps from UCSC in bed fromat. Scaffoldings that are not contained in the hg19.genome file are removed" in output
    assert "\t\x1b[1mSpecies:\x1b[0m Homo_sapiens" in output
    assert "\t\x1b[1mGenome Build:\x1b[0m hg19" in output
    assert "\t\x1b[1mKeywords:\x1b[0m gaps, regions, gap-locations, Assembly-Gaps, clone-gaps, contig-gaps, centromere-gaps, telomere-gaps, heterochromatin-gaps, short-arm-gaps" in output
    assert "\t\x1b[1mCached:\x1b[0m uploaded_to_aws" in output

    assert "\t\x1b[1mData Provider:\x1b[0m UCSC" in output
    assert "\t\x1b[1mData Version:\x1b[0m 22-Mar-2020" in output
    assert "\t\x1b[1mFile type(s):\x1b[0m bed" in output
    assert "\t\x1b[1mData file coordinate base:\x1b[0m 0-based-inclusive" in output
    assert "\t\x1b[1mIncluded Data Files:\x1b[0m" in output
    assert "\t\x1b[1mApproximate Data File Sizes:\x1b[0m" in output

    conda_root = temp_env
    assert "\t\x1b[1mPkg File Path:\x1b[0m {}/share/ggd/Homo_sapiens/hg19/hg19-gaps-ucsc-v1/1".format(conda_root) in output 
    assert "\t\x1b[1mInstalled Pkg Files:\x1b[0m " in output
    assert "\t\t{}/share/ggd/Homo_sapiens/hg19/hg19-gaps-ucsc-v1/1/hg19-gaps-ucsc-v1.bed.gz.tbi".format(conda_root) in output
    assert "\t\t{}/share/ggd/Homo_sapiens/hg19/hg19-gaps-ucsc-v1/1/hg19-gaps-ucsc-v1.bed.gz".format(conda_root) in output


    ## Remove temp env created in test_get_environment_variables()
    sp.check_output(["conda", "env", "remove", "--name", "temp_pkg_info_env"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


### list (List installed packages)

def test_load_json():  
    """
    Test that the load json file correctly returns a dictionary loaded from a json object 
    """

    pytest_enable_socket()
    
    ## Make file 
    file_name = "./tempjson.json"
    json_object = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Madeup_package': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/Madeup_package-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}}
    with open(file_name, "w") as fn:
        json.dump(json_object, fn)

    jdict = list_installed_pkgs.load_json(file_name)
    assert list(jdict["packages"].keys())[0] == "Madeup_package"
    assert jdict["packages"]["Madeup_package"]["version"] == "1"
    assert jdict["packages"]["Madeup_package"]["identifiers"]["genome-build"] == "hg19"
    assert jdict["packages"]["Madeup_package"]["identifiers"]["species"] == "Homo_sapiens"

    os.remove(file_name)


def test_get_environment_variables():
    """
    Test the get_environment_variables correctly gets the environment variables in the designated prefix
    """

    ## enable socket
    pytest_enable_socket()

    ## Test the hg19 gaps enviroment variable exists
    try:
        install_hg19_gaps_ucsc_v1()
    except:
        pass


    env_vars = list_installed_pkgs.get_environment_variables(utils.conda_root())
    assert "ggd_hg19_gaps_ucsc_v1_file" in env_vars.keys()
    assert "ggd_hg19_gaps_ucsc_v1_dir" in env_vars.keys()

    ## Test that "None" is returned for no enviroment variables
    assert list_installed_pkgs.get_environment_variables(os.path.join(utils.conda_root(),"BadPath")) == None

    ## Test using a different prefix
    ### Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env"])
    try: 
        shutil.rmtree(temp_env)
    except Exception:
        pass 
    ### Create conda environmnet 
    sp.check_output(["conda", "create", "--name", "temp_env"])

    ### Install ggd recipe using conda into temp_env
    ggd_package2 = "hg19-pfam-domains-ucsc-v1"
    install_args = Namespace(channel='genomics', command='install', debug=False, name=[ggd_package2], file=[], prefix = temp_env, id = None)
    assert install.install((), install_args) == True 

    env_vars = list_installed_pkgs.get_environment_variables(temp_env)
    assert "ggd_hg19_pfam_domains_ucsc_v1_file" in env_vars.keys()
    assert "ggd_hg19_pfam_domains_ucsc_v1_dir" in env_vars.keys()
    
    ## Keep pfam in temp_env for future tests


def test_list_pkg_info():
    """
    test the list_pkg_info function displays the correct info for the designated prefix
    """
    
    ## Test a normal run
    pkg_name = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    prefix = utils.conda_root()
    jdict = list_installed_pkgs.load_json(os.path.join(prefix,"share","ggd_info","channeldata.json"))
    env_vars = list_installed_pkgs.get_environment_variables(prefix)
    pkg_info = get_conda_package_list(prefix)


    ### Prefix not set
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_pkg_info([pkg_name],jdict["packages"],env_vars,pkg_info,prefix,False)
    output = temp_stdout.getvalue().strip() 
    assert pkg_name in output
    assert pkg_name.replace("-","_")+"_file" in output
    assert pkg_name.replace("-","_")+"_dir" in output
    assert "To use the environment variables run `source activate base" in output
    assert "You can see the available ggd data package environment variables by running `ggd show-env" in output
    assert "Name" in output and "Pkg-Version" in output and "Pkg-Build" in output and "Channel" in output and "Environment-Variables" in output

    ## prefix set
    pkg_name = "hg19-pfam-domains-ucsc-v1"
    ggd_channel = "genomics"
    prefix = temp_env = os.path.join(utils.conda_root(), "envs", "temp_env") ## From test_get_environment_variables()
    jdict = list_installed_pkgs.load_json(os.path.join(prefix,"share","ggd_info","channeldata.json"))
    env_vars = list_installed_pkgs.get_environment_variables(prefix)
    pkg_info = get_conda_package_list(prefix)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_pkg_info([pkg_name],jdict["packages"],env_vars,pkg_info,prefix,True)
    output = temp_stdout.getvalue().strip() 
    assert pkg_name in output
    assert pkg_name.replace("-","_")+"_file" in output
    assert pkg_name.replace("-","_")+"_dir" in output
    assert "The environment variables are only available when you are using the '{p}' conda environment".format(p=prefix) in output
    assert "Name" in output and "Pkg-Version" in output and "Pkg-Build" in output and "Channel" in output and "Environment-Variables" in output


def test_get_metadata():
    """
    Test the "get_metadata" function correctly returns the local meta-data json file
    """

    GGD_INFO = "share/ggd_info"
    METADATA = "channeldata.json"

    ## Get json dict
    metadata_dict = list_installed_pkgs.get_metadata(utils.conda_root(), GGD_INFO, METADATA)
    assert "packages" in metadata_dict
    assert "hg19-gaps-ucsc-v1" in metadata_dict["packages"]

    ## Test a bad file
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_installed_pkgs.get_metadata(utils.conda_root(), GGD_INFO, "BAD_METADATA_FILE.json")
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match(":ggd:list: !!ERROR!! Unable to load the local metadata")
    

def test_list_installed_packages():
    """
    Test the main function of ggd list
    """

    ## Normal Run
    args = Namespace(command='list', pattern=None, prefix=None, reset=False)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_installed_packages((), args)
    output = temp_stdout.getvalue().strip() 
    assert "hg19-gaps-ucsc-v1" in output
    assert "Name" in output and "Pkg-Version" in output and "Pkg-Build" in output and "Channel" in output and "Environment-Variables" in output
    assert "To use the environment variables run `source activate base" in output
    assert "You can see the available ggd data package environment variables by running `ggd show-env" in output

    ## Pattern set to exact package name
    args = Namespace(command='list', pattern="hg19-gaps-ucsc-v1", prefix=None, reset=False)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_installed_packages((), args)
    output = temp_stdout.getvalue().strip() 
    assert "hg19-gaps-ucsc-v1" in output
    assert "Name" in output and "Pkg-Version" in output and "Pkg-Build" in output and "Channel" in output and "Environment-Variables" in output
    assert "To use the environment variables run `source activate base" in output
    assert "You can see the available ggd data package environment variables by running `ggd show-env" in output

    ## Pattern set to beginning of package name
    args = Namespace(command='list', pattern="hg19", prefix=None, reset=False)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_installed_packages((), args)
    output = temp_stdout.getvalue().strip() 
    assert "hg19-gaps-ucsc-v1" in output
    assert "Name" in output and "Pkg-Version" in output and "Pkg-Build" in output and "Channel" in output and "Environment-Variables" in output
    assert "To use the environment variables run `source activate base" in output
    assert "You can see the available ggd data package environment variables by running `ggd show-env" in output

    ## Pattern set to middle of package name
    args = Namespace(command='list', pattern="gaps", prefix=None, reset=False)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_installed_packages((), args)
    output = temp_stdout.getvalue().strip() 
    assert "hg19-gaps-ucsc-v1" in output
    assert "Name" in output and "Pkg-Version" in output and "Pkg-Build" in output and "Channel" in output and "Environment-Variables" in output
    assert "To use the environment variables run `source activate base" in output
    assert "You can see the available ggd data package environment variables by running `ggd show-env" in output

    ## Pattern does not match an installed package
    args = Namespace(command='list', pattern="BADPATTERN", prefix=None, reset=False)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_installed_pkgs.list_installed_packages((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("'{p}' did not match any installed data packages".format(p="BADPATTERN"))

    ## Package in set prefix (Not conda_root)
    p = os.path.join(utils.conda_root(), "envs", "temp_env") ## From test_get_environment_variables()
    args = Namespace(command='list', pattern=None, prefix=p, reset=False)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_installed_packages((), args)
    output = temp_stdout.getvalue().strip() 
    assert "hg19-pfam-domains-ucsc-v1" in output
    assert "Name" in output and "Pkg-Version" in output and "Pkg-Build" in output and "Channel" in output and "Environment-Variables" in output
    assert "The environment variables are only available when you are using the '{}' conda environment".format(p) in output

    ## Package in set prefix (Not conda_root) and using the prefix name rather than the prefix path
    args = Namespace(command='list', pattern=None, prefix="temp_env", reset=False)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_installed_packages((), args)
    output = temp_stdout.getvalue().strip() 
    assert "hg19-pfam-domains-ucsc-v1" in output
    assert "Name" in output and "Pkg-Version" in output and "Pkg-Build" in output and "Channel" in output and "Environment-Variables" in output
    assert "The environment variables are only available when you are using the '{}' conda environment".format(p) in output

    ## Remove "hg19-pfam-domains-ucsc-v1" from temp_env conda metadata but not ggd 
    metadata_path = "share/ggd_info/channeldata.json"
    full_path = os.path.join(utils.get_conda_prefix_path("temp_env"), metadata_path)
    
    ## Check that the package is still displayed, but a warning is provided about it is missing from conda metadata
    sp.check_output(["conda", "uninstall", "hg19-pfam-domains-ucsc-v1", "-p", utils.get_conda_prefix_path("temp_env")])
    with redirect_stdout(temp_stdout):
        list_installed_pkgs.list_installed_packages((), args)
    output = temp_stdout.getvalue().strip() 
    assert "hg19-pfam-domains-ucsc-v1" in output
    assert "[WARNING: Present in GGD but missing from Conda]" in str(output)
    assert ("NOTE: Packages with the '[WARNING: Present in GGD but missing from Conda]' messages represent packages where the ggd"
            " package(s) are installed, but the package metadata has been removed from conda storage. This" 
            " happens when one of the following happen: \n 1) The package represents an ID specific meta-"
            "recipe intsalled by GGD. \n 2) When the recipe is built locally using 'ggd check-recipe' and"
            " has not been uninstalled. (Commonly for private data packages).\n  Or \n 3) The package is" 
            " uninstalled using conda rather then ggd. The package is still available for use and is in"
            " the same state as before the 'conda uninstall'. To fix the problem on conda's side, uninstall"
            " the package with 'ggd uninstall' and re-install with 'ggd install'.\n"
            )

    ## Remove temp env created in test_get_environment_variables()
    sp.check_output(["conda", "env", "remove", "--name", "temp_env"])
    try:
        shutil.rmtree(p)
    except Exception:
        pass
    assert os.path.exists(p) == False

    ## Test basic reset works
    args = Namespace(command='list', pattern=None, prefix=None, reset=True)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_installed_pkgs.list_installed_packages((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("0") ## check that the exit code is 1


### predict-path

def test_get_ggd_metadata():
    """ 
    Test that the get_ggd_metadata properly works 
    """

    pytest_enable_socket()

    metadata = predict_path.get_ggd_metadata("genomics")
    assert len(metadata["packages"]) > 0

    ## Test without internet connection
    pytest_disable_socket()

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        predict_path.get_ggd_metadata("genomics")
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("A internet connection is required to use this function. Please try again when you have secured an internet connection") 

    pytest_enable_socket()


def test_predict_path():
    """
    Test the main method of predict-path
    """
    pytest_enable_socket()

    ## Testing with grch37-autosomal-dominant-genes-berg-v1 data package
    
    ## Test bad package name
    args = Namespace(channel='genomics', command='predict-path', file_name='grch37-autosomal-dominant-genes-berg-v1.bed.gz', package_name='bad_package_name-grch37-autosomal-dominant-genes-berg-v1', prefix=None, dir_path = False, id = None)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        predict_path.predict_path((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("The {pn} data package is not one of the packages in the ggd-{c} channel".format(pn="bad_package_name-grch37-autosomal-dominant-genes-berg-v1", c="genomics"))


    ## Test bad file name
    args = Namespace(channel='genomics', command='predict-path', file_name='autodom-genes-berg', package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=None,  dir_path = False, id = None)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        predict_path.predict_path((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("The autodom-genes-berg file is not one of the files listed for this package. The files installed by this package are")


    ## Test closest file name
    args = Namespace(channel='genomics', command='predict-path', file_name='grch37-autosomal-dominant-genes-berg-v1', package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=None,  dir_path = False, id = None)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(utils.conda_root(),"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1","grch37-autosomal-dominant-genes-berg-v1.bed.gz") in str(output)
    

    ## Test closest file name
    args = Namespace(channel='genomics', command='predict-path', file_name='berg-v1.compliment', package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=None,  dir_path = False, id = None)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(utils.conda_root(),"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1","grch37-autosomal-dominant-genes-berg-v1.compliment.bed.gz") in str(output)


    ## Test full name file name
    args = Namespace(channel='genomics', command='predict-path', file_name='grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi', package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=None,  dir_path = False, id = None)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(utils.conda_root(),"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1","grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi") in str(output)
    

    ## Test no file-name or dir-path
    args = Namespace(channel='genomics', command='predict-path', file_name=None, package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=None,  dir_path = False, id = None)

    temp_stdout = StringIO()
    with pytest.raises(SystemExit) as pytest_wrapped_e, redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:predict-path: !!ERROR!! Either the '--file-name' or the '--dir-path' argument is required. Neither was given" in output


    ## Test prdiction in different environmnet
    ### Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "predict-path")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "predict-path"])
    try: 
        shutil.rmtree(temp_env)
    except Exception:
        pass 
    ### Create conda environmnet 
    sp.check_output(["conda", "create", "--name", "predict-path"])

    ## Test full name file name
    args = Namespace(channel='genomics', command='predict-path', file_name='grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi', package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=temp_env,  dir_path = False, id = None)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(temp_env,"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1","grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi") in str(output)


    ## Test full name file name and that the ID is ignored for a non meta-recipe
    args = Namespace(channel='genomics', command='predict-path', file_name='grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi', package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=temp_env,  dir_path = False, id = "SOME ID")

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(temp_env,"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1","grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi") in str(output)


    ## Test full name file name and dir-path. (File name should be used over dir path)
    args = Namespace(channel='genomics', command='predict-path', file_name='grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi', package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=temp_env,  dir_path = True, id = None)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(temp_env,"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1","grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi") in str(output)

    ## Test dir path
    args = Namespace(channel='genomics', command='predict-path', file_name=None, package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=temp_env,  dir_path = True, id = None)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(temp_env,"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1") in str(output)
    assert os.path.join(temp_env,"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1","grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi") not in str(output)


    ## Test dir path and that the ID is ignored for a non meta-recipe
    args = Namespace(channel='genomics', command='predict-path', file_name=None, package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=temp_env,  dir_path = True, id = "SOME_ID")

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(temp_env,"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1") in str(output)
    assert os.path.join(temp_env,"share","ggd", "Homo_sapiens","GRCh37","grch37-autosomal-dominant-genes-berg-v1","1","grch37-autosomal-dominant-genes-berg-v1.bed.gz.tbi") not in str(output)


    ## Test meta-recipe without an ID
    args = Namespace(channel='genomics', command='predict-path', file_name=None, package_name='meta-recipe-geo-accession-geo-v1', prefix=temp_env,  dir_path = True, id = None)

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(temp_env,"share","ggd", "meta-recipe","meta-recipe","meta-recipe-geo-accession-geo-v1","1") in str(output)


    ## Test meta-recipe with an ID and  that the id is set to lower case
    args = Namespace(channel='genomics', command='predict-path', file_name=None, package_name='meta-recipe-geo-accession-geo-v1', prefix=temp_env,  dir_path = True, id = "GSE123")

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args)
    output = temp_stdout.getvalue().strip() 
    assert os.path.join(temp_env,"share","ggd", "meta-recipe","meta-recipe","gse123-geo-v1","1") in str(output)


    ## Remove temp env created in test_get_environment_variables()
    sp.check_output(["conda", "env", "remove", "--name", "predict-path"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


    ## Test the predict path is the same path as an installed file
    install_args = Namespace(channel='genomics', command='install', debug=False, name=["grch37-autosomal-dominant-genes-berg-v1"], file=[], prefix=None, id = None)
    assert install.install((), install_args) == True 

    list_files
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name="grch37-autosomal-dominant-genes-berg-v1", pattern="grch37-autosomal-dominant-genes-berg-v1.bed.gz", prefix=None, species=None, version=None)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_files.list_files((),args)
    output = str(temp_stdout.getvalue().strip()) 
    assert os.path.exists(str(output))

    args2 = Namespace(channel='genomics', command='predict-path', file_name='grch37-autosomal-dominant-genes-berg-v1.bed.gz', package_name='grch37-autosomal-dominant-genes-berg-v1', prefix=None,  dir_path = False, id = None)
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        predict_path.predict_path((), args2)
    output2 = temp_stdout.getvalue().strip() 

    assert str(output2) == str(output)

    sp.check_call(["ggd","uninstall","grch37-autosomal-dominant-genes-berg-v1"])


#--------------------------------------------------------
## Test functions based on hg19-gaps not being installed
#--------------------------------------------------------


def test_show_env_no_envvars():
    pytest_enable_socket()

    ## uninstalled hg19_gaps() testing 
    uninstall_hg19_gaps_ucsc_v1()
    parser = ()
    args = Namespace(command='show-env', pattern=None)
    dir_env_var_name_dir = "$ggd_hg19_gaps_v1_dir"
    file_env_var_name_file = "$ggd_hg19_gaps_v1_file"

    ## Test a normal run
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.show_env(parser,args)
    output = temp_stdout.getvalue().strip() 
    assert (dir_env_var_name_dir not in output)
    assert (file_env_var_name_file not in output)

            
