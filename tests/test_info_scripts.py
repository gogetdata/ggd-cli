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
from helpers import install_hg19_gaps_ucsc_v1, uninstall_hg19_gaps_ucsc_v1, CreateRecipe
from ggd import show_env
from ggd import list_files
from ggd import list_pkg_info
from ggd import utils
from ggd import install

if sys.version_info[0] == 3:
    from io import StringIO
elif sys.version_info[0] == 2:
    from StringIO import StringIO


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
# Unit Test for ggd show-env, ggd list-files, and ggd pkg-info
#-----------------------------------------------------------------------------------------------------------------------


#----------------------------------------------------
## Test functions based on hg19-gaps being installed
#----------------------------------------------------


### Show-env

def test_show_env_goodrun():
    """
    Test that show_env functoin properly provides the environment variable for an installed package
    """
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
    with open(active_loc, "a") as a:
        a.write(active_var)
    with open(deactive_loc, "a") as d:
        d.write(deactive_var)
    

def test_remove_env_variable():
    """
    Test that the remove_env_varial correctly removes the env var from the activated.d/env_vars.sh file
    """
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


def test_activate_environment_variables():
    """
    Test that the activate_environment_variables function properly activates the environment variables
    """
    dir_env_var_name = "$ggd_hg19_gaps_ucsc_v1_dir"
    file_env_var_name = "$ggd_hg19_gaps_ucsc_v1_file"
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        show_env.activate_enviroment_variables()
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

    matching_vars = {'ggd_hg38_gaps_11_mar_2019': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-gaps_11-mar-2019/1', 'ggd_hg38_reference_genome_ucsc': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-reference-genome-ucsc/1', 'ggd_hg38_cpg_islands': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-cpg-islands/1', 'ggd_grch38_reference_genome_ensembl': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/GRCh38/grch38-reference-genome-ensembl/1', 'ggd_hg19_cpg_islands': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg19/hg19-cpg-islands/1', 'ggd_hg19_gaps': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg19/hg19-gaps/1', 'ggd_hg19_reference_genome_ucsc': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg19/hg19-reference-genome-ucsc/1', 'ggd_hg38_simplerepeats': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-simplerepeats/1', 'ggd_hg19_pfam_domains_ucsc': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg19/hg19-pfam-domains-ucsc/1', 'ggd_grch37_esp_variants': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/GRCh37/grch37-esp-variants/1', 'ggd_hg38_pfam_domains_ucsc': '/uufs/chpc.utah.edu/common/home/quinlan-ucgdstor/u1138933/ucgdscratch/anaconda2/share/ggd/Homo_sapiens/hg38/hg38-pfam-domains-ucsc/1'}
    active = [x for x in matching_vars if x in os.environ and os.environ[x] == matching_vars[x]]  
    inactive = [x for x in matching_vars if x not in active]

    active_list, inactive_list = show_env.test_vars(matching_vars)

    for var in active_list:
        assert var in active 

    for var in inactive_list:
        assert var in inactive


### List files

def test_in_ggd_channel():
    """
    Test that the in_ggd_channel from ggd list-files works correctly 
    """
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
    assert pytest_wrapped_e.match("1") ## check that the exit code is 1

    
    ## test that in_ggd_channel properly handels bad recipe name 
    ggd_package = "NOT_A_REAL_PACKAGE_NAME"
    channel = "genomics"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.in_ggd_channel(ggd_package, channel)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## check that the exit code is 1


def test_list_files():
    """
    Test the main method of list-files 
    """

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
    assert pytest_wrapped_e.match("1") ## check that the exit code is 1

    ##Test that the function exits if a bad genome build is given
    args = Namespace(channel='genomics', command='list-files', genome_build="Bad_Build", name=ggd_package, pattern=None, species=None, prefix=None, version=None)
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.list_files((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## check that the exit code is 1

    ##Test that the function exits if a bad species is given
    args = Namespace(channel='genomics', command='list-files', genome_build=None, name=ggd_package, pattern=None, prefix=None, species="Mus_musculus", version=None)
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_files.list_files((), args)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## check that the exit code is 1

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


def test_list_file_with_prefix():

    ## Temp conda environment 
    temp_env = os.path.join(utils.conda_root(), "envs", "temp_env")
    ### Remove temp env if it already exists
    sp.check_output(["conda", "env", "remove", "--name", "temp_env"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    ## Create conda environmnet 
    sp.check_output(["conda", "create", "--name", "temp_env"])

    ## Install ggd recipe using conda into temp_env
    ggd_package = "hg19-pfam-domains-ucsc-v1"
    install_args = Namespace(channel='genomics', command='install', debug=False, name=ggd_package, version='-1', prefix = temp_env)
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
    
    ## Remove temp env
    sp.check_output(["conda", "env", "remove", "--name", "temp_env"])
    try:
        shutil.rmtree(temp_env)
    except Exception:
        pass
    assert os.path.exists(temp_env) == False


### pkg-info

def test_list_all_versions():
    """
    Test that the list all versions handles different situations correctly 
    """
    
    ### Test that all vresion of a hg19-gaps in the ggd-dev channel are properly listed

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


    ### Test that a bad channel name is correctly handled 

    ggd_package = "hg19-gaps"
    ggd_channel = "BAD_CHANNEL"

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.list_all_versions(ggd_package, ggd_channel)
    output = temp_stdout.getvalue().strip() 
    assert "No version information for "+ggd_package+" in the ggd-"+ggd_channel+" channel" in output

    assert list_pkg_info.list_all_versions(ggd_package, ggd_channel) == False


    ### Test that a bad package name is correctly handled 

    ggd_package = "Bad_package"
    ggd_channel = "dev"

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.list_all_versions(ggd_package, ggd_channel)
    output = temp_stdout.getvalue().strip() 
    assert "No version information for "+ggd_package+" in the ggd-"+ggd_channel+" channel" in output

    assert list_pkg_info.list_all_versions(ggd_package, ggd_channel) == False


def test_check_if_ggd_recipe():
    """
    Test if check_if_ggd_recipe correclty identifies if a ggd recipe is a recipe or not
    """

    ## Test a normal package name and channel
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    assert list_pkg_info.check_if_ggd_recipe(ggd_package, ggd_channel) == True

    ## Test a normal package name but bad channel
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "BAD_CHANNEL"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        list_pkg_info.check_if_ggd_recipe(ggd_package, ggd_channel)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that systemexit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## check that the exit code is 1

    ## Test a bad package name and normal channel
    ggd_package = "BAD_Recipe"
    ggd_channel = "genomics"
    assert list_pkg_info.check_if_ggd_recipe(ggd_package, ggd_channel) == False


def test_get_pkg_info():
    """
    Test that get_pkg_info correctly returns the pkg info or handles other problems 
    """

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


    ## Test get_meta_yaml_info function correctly returns output for a recipe without a cached key and without a dataversion key 

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
        lines = output.strip().split("\n")
        assert lines[0] == "GGD-Recipe: fake-recipe2"
        assert lines[1] == "GGD-Channel: {}-{}".format("ggd",ggd_channel)
        assert lines[2] == "Summary: A fake recipe for testing"
        assert lines[3] == "Pkg Version: 1"
        assert lines[4] == "Pkg Build: 1"
        assert lines[5] == "Species: Homo_sapiens"
        assert lines[6] == "Genome Build: hg19"
        assert lines[7] == "Keywords: gaps, region"
        conda_root = utils.conda_root()
        assert lines[8] == "Pkg File Path: {}/share/ggd/Homo_sapiens/hg19/fake-recipe2/1".format(conda_root)
        assert lines[9] == "Pkg Files:" 
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
    

    ## Test get_meta_yaml_info function correctly returns output for a recipe with a cached key and a dataversion key 

    recipe = CreateRecipe(

        """
        fake-recipe3:
            meta.yaml: |
                build:
                  binary_relocation: false
                  detect_binary_files_with_prefix: false
                  noarch: generic
                  number: 1
                extra:
                  authors: me
                package:
                  name: fake-recipe3
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
                    data-version: Today
                    ggd-channel: Newchannel 

        """, from_string=True)

    recipe.write_recipes()

    ggd_package = "fake-recipe3"
    ggd_channel = "Newchannel"
    meta_yaml_file = os.path.join(recipe.recipe_dirs[ggd_package],"meta.yaml")

    try:
        f = open(meta_yaml_file, "r")

        temp_stdout = StringIO()
        with redirect_stdout(temp_stdout):
            list_pkg_info.get_meta_yaml_info(f,ggd_package,ggd_channel)
        output = temp_stdout.getvalue().strip() 
        lines = output.strip().split("\n")
        assert lines[0] == "GGD-Recipe: fake-recipe3"
        assert lines[1] == "GGD-Channel: {}-{}".format("ggd",ggd_channel)
        assert lines[2] == "Summary: A fake recipe for testing"
        assert lines[3] == "Pkg Version: 1"
        assert lines[4] == "Pkg Build: 1"
        assert lines[5] == "Species: Homo_sapiens"
        assert lines[6] == "Genome Build: hg19"
        assert lines[7] == "Keywords: gaps, region"
        assert lines[8] == "Data Version: Today"
        assert lines[9] == "Cached: uploaded_to_aws"
        conda_root = utils.conda_root()
        assert lines[10] == "Pkg File Path: {}/share/ggd/Homo_sapiens/hg19/fake-recipe3/1".format(conda_root)
        assert lines[11] == "Pkg Files:" 
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


    ## Normal run with all version dispalyed 
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    args = Namespace(all_versions=True, channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=False)
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
    assert "-> Listing all ggd-recipe version for the {} recipe in the ggd-{} channel".format(ggd_package,ggd_channel) in output

    ## Normal run with print recipes 
    ggd_package = "hg19-gaps-ucsc-v1"
    ggd_channel = "genomics"
    args = Namespace(all_versions=False, channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=True)
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
    assert "{} recipe file:\n***********************".format(ggd_package) in output 


    ## Bad recipe run
    ggd_package = "Bad-recipe"
    ggd_channel = "genomics"
    args = Namespace(all_versions=False, channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=False)
    assert list_pkg_info.info((),args) == False

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.info((),args)
    output = temp_stdout.getvalue().strip() 
    assert "-> The {} package is not in the ggd-{} channel.".format(ggd_package, ggd_channel) in output 


    ## Bad recipe run with all versions
    ggd_package = "Bad-recipe"
    ggd_channel = "genomics"
    args = Namespace(all_versions=True, channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=False)
    assert list_pkg_info.info((),args) == False

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.info((),args)
    output = temp_stdout.getvalue().strip() 
    assert "-> The {} package is not in the ggd-{} channel.".format(ggd_package, ggd_channel) in output 


    ## Bad recipe run with print recipe
    ggd_package = "Bad-recipe"
    ggd_channel = "genomics"
    args = Namespace(all_versions=False, channel=ggd_channel, command='pkg-info', name=ggd_package, show_recipe=True)
    assert list_pkg_info.info((),args) == False

    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        list_pkg_info.info((),args)
    output = temp_stdout.getvalue().strip() 
    assert "-> The {} package is not in the ggd-{} channel.".format(ggd_package, ggd_channel) in output 



#--------------------------------------------------------
## Test functions based on hg19-gaps not being installed
#--------------------------------------------------------


def test_show_env_no_envvars():
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

            
