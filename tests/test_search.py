from __future__ import print_function
import os
import sys
import subprocess as sp
import pytest
import yaml
import tempfile
import requests
import argparse
import contextlib
import json
from ggd import search 
from ggd import utils
from ggd import list_files
from helpers import install_hg19_gaps_ucsc_v1, uninstall_hg19_gaps_ucsc_v1
from argparse import Namespace
from argparse import ArgumentParser

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

TEST_LABEL = "ggd-search-test"


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

#-------------------------------------------------------------------------------------------------------
## Unit Tests for ggd search
#-------------------------------------------------------------------------------------------------------

def test_load_json_goodjson():  

    pytest_enable_socket()
    
    ## Make file 
    file_name = "./tempjson.json"
    json_object = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Madeup_package': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/Madeup_package-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}}
    with open(file_name, "w") as fn:
        json.dump(json_object, fn)

    jdict = search.load_json(file_name)
    assert list(jdict["packages"].keys())[0] == "Madeup_package"
    assert jdict["packages"]["Madeup_package"]["version"] == "1"
    assert jdict["packages"]["Madeup_package"]["identifiers"]["genome-build"] == "hg19"
    assert jdict["packages"]["Madeup_package"]["identifiers"]["species"] == "Homo_sapiens"

    os.remove(file_name)


def test_load_json_from_url_badurl():
    """
    Test if a bad url fails to load
    """
    pytest_enable_socket()
            
    bad_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/channeldata/NOTAREALCHANNEL.channeldata.json"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.load_json_from_url(bad_url)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1


def test_load_json_from_url_goodurl():
    """
    test if a good url does load
    """
    pytest_enable_socket()
            
    good_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/channeldata/genomics/channeldata.json"
    assert search.load_json_from_url(good_url)


def test_search_package_madeup_package():
    """
    Test the search_pacakge method to see if it properly identifies a madeup package
    """
    pytest_enable_socket()
            
    name = "Madeup-package"
    search_term = "madeup-pack"
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Madeup_package': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/Madeup_package-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}}

    ## Default match score >= 50
    assert search.search_packages(json_dict,[search_term],score_cutoff=50) == ["Madeup_package"]
    assert search.search_packages(json_dict,[search_term],score_cutoff=70) == ["Madeup_package"]

    search_term = "maed pakacage"
    ## Default match score >= 50
    assert search.search_packages(json_dict,[search_term],score_cutoff=50) == ["Madeup_package"]
    assert search.search_packages(json_dict,[search_term],score_cutoff=90) == []


def test_search_package_madeup_package_badsearchterm():
    """
    Test the search_pacakge method to see if it returns no package based on bad search terms
    """
    pytest_enable_socket()
            
    name = "Madeup-package"
    search_term = "NOWAY"
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Madeup_package': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/Madeup_package-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}}

    ## Default match score >= 50
    assert search.search_packages(json_dict,[search_term]) == []
    assert search.search_packages(json_dict,[search_term],score_cutoff=25) == []
    assert search.search_packages(json_dict,[search_term],score_cutoff=0) == ["Madeup_package"]
   
    search_term = "BAD SEARCH"
    ## Default match score >= 50
    assert search.search_packages(json_dict,[search_term],score_cutoff=75) == []
    assert search.search_packages(json_dict,[search_term],score_cutoff=0) == ["Madeup_package"]


def test_search_packages_keyword_match():

    name = "hg19-gaps-ucsc-v1"
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps-ucsc-v1': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], 
                    u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, 
                    u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, 
                    u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': 
                    u'noarch/hg19-gaps-ucsc-v1-1-1.tar.bz2', u'pre_link': False, 
                    u'keywords': [u'gaps', u'region', u'TEST-KEYWORD',u'GENOMICS-KEYWORD'], 
                    u'summary': u'Assembly gaps from USCS', u'text_prefix': False, 
                    u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}} 

    search_term = "TEST-KEYWORD"
    assert search.search_packages(json_dict,[search_term]) == ["hg19-gaps-ucsc-v1"]
    search_term = search_term.lower()
    assert search.search_packages(json_dict,[search_term]) == ["hg19-gaps-ucsc-v1"]
    search_term = "GENOMICS-KEYWORD"
    assert search.search_packages(json_dict,[search_term]) == ["hg19-gaps-ucsc-v1"]
    search_term = search_term.lower()
    assert search.search_packages(json_dict,[search_term]) == ["hg19-gaps-ucsc-v1"]
    search_term = "TEST-WORD"
    assert search.search_packages(json_dict,[search_term]) == ["hg19-gaps-ucsc-v1"]
    search_term = search_term.lower()
    assert search.search_packages(json_dict,[search_term]) == ["hg19-gaps-ucsc-v1"]
    search_term = "GENOM-KEY"
    assert search.search_packages(json_dict,[search_term]) == ["hg19-gaps-ucsc-v1"]
    search_term = search_term.lower()
    assert search.search_packages(json_dict,[search_term]) == ["hg19-gaps-ucsc-v1"]
    search_term = "BAD-IDENTIFIER-KEY"
    assert search.search_packages(json_dict,[search_term]) == []
    search_term = search_term.lower()
    assert search.search_packages(json_dict,[search_term]) == []


def test_check_installed():
    """
    test the check_installed function properly identifies if something is already installed or not, and provides the path for it
    """
    pytest_enable_socket()
            
    ## json dict
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-gaps-v1': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-gaps-ucsc-v1': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-ucsc-v1-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'hg38 cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg38-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'10-Aug-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg38 reference genome from UCSC. This version includes the latest patch, patch 12. (url:http://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/p12/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The GRCh37 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'25-May-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg19 reference genome from UCSC. This version includes the latest patch, patch 13. (http://hgdownload.soe.ucsc.edu/goldenPath/hg19/hg19Patch13/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'ESP variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'18-Nov-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-phastcons': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'09-Feb-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-phastcons-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'phastCons', u'conservation'], u'summary': u'phastCons scores for MSA of 99 genomes to hg19', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## ggd package not installed
    ggd_recipe = "hg19-reference-genome-ucsc" 
    isinstalled, path = search.check_installed(ggd_recipe, json_dict)
    assert isinstalled == False
    assert path == None

    ## GGD package that is installed
    ### Install hg19-gaps-ucsc-v1
    ggd_recipe = "hg19-gaps-ucsc-v1"
    try:
        install_hg19_gaps_ucsc_v1()
    except:
        pass

    ### Check that it is installed
    isinstalled, path = search.check_installed(ggd_recipe, json_dict)
    assert isinstalled == True
    species = json_dict["packages"][ggd_recipe]["identifiers"]["species"]
    build = json_dict["packages"][ggd_recipe]["identifiers"]["genome-build"]
    version = json_dict["packages"][ggd_recipe]["version"]
    assert path == os.path.join(utils.conda_root(),"share","ggd",species,build,ggd_recipe,version) 


def test_filter_by_identifiers_genome_build():  

    pytest_enable_socket()
    
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'hg38 cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg38-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'10-Aug-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg38 reference genome from UCSC. This version includes the latest patch, patch 12. (url:http://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/p12/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The GRCh37 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'25-May-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg19 reference genome from UCSC. This version includes the latest patch, patch 13. (http://hgdownload.soe.ucsc.edu/goldenPath/hg19/hg19Patch13/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'ESP variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'18-Nov-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-phastcons': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'09-Feb-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-phastcons-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'phastCons', u'conservation'], u'summary': u'phastCons scores for MSA of 99 genomes to hg19', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## Test fail because match list is empty
    filter_term = "hg19"
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        search.filter_by_identifiers([],json_dict,[filter_term])
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:search: WARNING: Unable to filter packages using: 'hg19'" in output
    assert "The un-filtered list will be used" in output

    ## Test filter based on "hg19" genome build
    iden_keys = ["genome-build"]
    filter_term = ["hg19"]
    assert search.filter_by_identifiers(iden_keys,json_dict,filter_term) == {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'25-May-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg19 reference genome from UCSC. This version includes the latest patch, patch 13. (http://hgdownload.soe.ucsc.edu/goldenPath/hg19/hg19Patch13/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-phastcons': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'09-Feb-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-phastcons-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'phastCons', u'conservation'], u'summary': u'phastCons scores for MSA of 99 genomes to hg19', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}} 

    ## Test filter based on "hg38" genome build
    iden_keys = ["genome-build"]
    filter_term = ["hg38"]
    assert search.filter_by_identifiers(iden_keys,json_dict,filter_term) == {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg38-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'hg38 cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg38-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg38-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'10-Aug-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg38 reference genome from UCSC. This version includes the latest patch, patch 12. (url:http://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/p12/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg38-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'18-Nov-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## Test unable to filter based on bad genome build
    iden_keys = ["genome-build"]
    filter_term = ["Bad-genome-build"]
    ## Assert that if a the filter term was unable to filter anything the original list is returned
    assert search.filter_by_identifiers(iden_keys,json_dict,filter_term) == json_dict 


def test_filter_by_identifiers_bad_identifier():
    """
    Test that the filter_by_idenfiiers function correclty processes a bad identifier key passed to the function 
    """
    pytest_enable_socket()
            

    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'hg38 cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg38-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'10-Aug-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg38 reference genome from UCSC. This version includes the latest patch, patch 12. (url:http://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/p12/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The GRCh37 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'25-May-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg19 reference genome from UCSC. This version includes the latest patch, patch 13. (http://hgdownload.soe.ucsc.edu/goldenPath/hg19/hg19Patch13/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'ESP variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'18-Nov-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-phastcons': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'09-Feb-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-phastcons-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'phastCons', u'conservation'], u'summary': u'phastCons scores for MSA of 99 genomes to hg19', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## Test fail because match list is empty
    key = ["Bad-Identifier"]
    filter_term = ["hg19"]
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        search.filter_by_identifiers(key,json_dict,filter_term)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:search: WARNING: Unable to filter packages using: 'hg19'" in output
    assert "The un-filtered list will be used" in output

    ## Test filter identifiers returns original list if the identifiers key is not in the identifiers dictionary
    assert search.filter_by_identifiers(key,json_dict,filter_term) == json_dict


def test_filter_by_identifiers_species():
    """
    Test the filter by idenfiiers function using species 
    """
    pytest_enable_socket()
            

    ## Create json dictionary with Homo_sapiens, Mus_musculus, and Drosophila_melanogaster species.
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'dm3-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm3-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'dm3 cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm3', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm10-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'dm6-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'10-Aug-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm6-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The dm6 reference genome from UCSC. This version includes the latest patch, patch 12. (url:http://hgdownload.soe.ucsc.edu/goldenPath/dm6/bigZips/p12/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm6', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm9-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The mm9 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'dm3-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'25-May-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm3-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The dm3 reference genome from UCSC. This version includes the latest patch, patch 13. (http://hgdownload.soe.ucsc.edu/goldenPath/hg19/hg19Patch13/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm3', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm10-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'mm10 variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'dm6-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'18-Nov-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm6-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm6', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm9-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'dm3-phastcons': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'09-Feb-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm3-phastcons-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'phastCons', u'conservation'], u'summary': u'phastCons scores for MSA of 99 genomes to dm3', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm3', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm10-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## Test fail because match list is empty
    filter_term = ["Homo_sapiens"]
    temp_stdout = StringIO()
    with redirect_stdout(temp_stdout):
        search.filter_by_identifiers([],json_dict,filter_term)
    output = temp_stdout.getvalue().strip() 
    assert ":ggd:search: WARNING: Unable to filter packages using: 'Homo_sapiens'" in output
    assert "The un-filtered list will be used" in output

    ## Test filter based on "Homo_sapiens" species
    key = ["species"]
    filter_term = ["Homo_sapiens"]
    assert search.filter_by_identifiers(key,json_dict,filter_term) == {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## Test filter based on "Drosophila_melanogaster" species
    key = ["species"]
    filter_term = ["Drosophila_melanogaster"]
    assert search.filter_by_identifiers(key,json_dict,filter_term) == {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'dm3-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm3-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'dm3 cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm3', u'species': u'Drosophila_melanogaster'}}, 
                    u'dm6-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'10-Aug-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm6-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The dm6 reference genome from UCSC. This version includes the latest patch, patch 12. (url:http://hgdownload.soe.ucsc.edu/goldenPath/dm6/bigZips/p12/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm6', u'species': u'Drosophila_melanogaster'}}, 
                    u'dm3-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'25-May-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm3-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The dm3 reference genome from UCSC. This version includes the latest patch, patch 13. (http://hgdownload.soe.ucsc.edu/goldenPath/hg19/hg19Patch13/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm3', u'species': u'Drosophila_melanogaster'}}, 
                    u'dm6-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'18-Nov-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm6-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm6', u'species': u'Drosophila_melanogaster'}}, 
                    u'dm3-phastcons': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'09-Feb-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm3-phastcons-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'phastCons', u'conservation'], u'summary': u'phastCons scores for MSA of 99 genomes to dm3', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm3', u'species': u'Drosophila_melanogaster'}}}} 

    ## Test filter based on "Mus_musculus" species
    key = ["species"]
    filter_term = ["Mus_musculus"]
    assert search.filter_by_identifiers(key,json_dict,filter_term) == {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'mm10-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'mm9-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The mm9 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'mm10-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'mm10 variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'mm9-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'mm10-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}}} 

    ## Test unable to filter based on bad species
    key = ["species"]
    filter_term = ["Bad-species"]
    assert search.filter_by_identifiers(key,json_dict,filter_term) == json_dict


def test_filter_by_identifiers_multiple_identifiers():
    """
    test the filter_by_identiifers with multiple identifiers used
    """
    ## Create json dictionary with Homo_sapiens, Mus_musculus, and Drosophila_melanogaster species.
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'dm3-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm3-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'dm3 cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm3', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm10-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'dm6-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'10-Aug-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm6-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The dm6 reference genome from UCSC. This version includes the latest patch, patch 12. (url:http://hgdownload.soe.ucsc.edu/goldenPath/dm6/bigZips/p12/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm6', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm9-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The mm9 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'dm3-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'25-May-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm3-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The dm3 reference genome from UCSC. This version includes the latest patch, patch 13. (http://hgdownload.soe.ucsc.edu/goldenPath/hg19/hg19Patch13/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm3', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm10-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'mm10 variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'dm6-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'18-Nov-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm6-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm6', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm9-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'dm3-phastcons': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'09-Feb-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/dm3-phastcons-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'phastCons', u'conservation'], u'summary': u'phastCons scores for MSA of 99 genomes to dm3', u'text_prefix': False, u'identifiers': {u'genome-build': u'dm3', u'species': u'Drosophila_melanogaster'}}, 
                    u'mm10-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## Test thatt unequal iden_keys and filter terms returns the same dict
    iden_keys = ["species","species","genome-build"]
    filter_terms = ["Homo_sapiens","Mus_musculus"]
    assert search.filter_by_identifiers(iden_keys,json_dict,filter_terms) == json_dict

    ## Test that multiple iden keys work. Genome build should take precedence over species. Otherwise, any recipe with identified species would print 
    ## Will keep all Homo_sapiens, not just hg19
    iden_keys = ["species","genome-build"]
    filter_terms = ["Homo_sapiens","hg19"]
    assert search.filter_by_identifiers(iden_keys,json_dict,filter_terms) == {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## Test that multiple iden keys work with different species and genome builds 
    iden_keys = ["species","species"]
    filter_terms = ["Homo_sapiens","Mus_musculus"]
    assert search.filter_by_identifiers(iden_keys,json_dict,filter_terms) == {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'mm10-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'mm9-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The mm9 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'mm10-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'mm10 variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'mm9-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'mm10-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## Test different species for genome build
    iden_keys = ["species","genome-build"]
    filter_terms = ["Mus_musculus","hg19"]
    assert search.filter_by_identifiers(iden_keys,json_dict,filter_terms) == {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'mm10-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'mm9-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The mm9 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'mm10-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'mm10 variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'mm9-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm9-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm9', u'species': u'Mus_musculus'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'mm10-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/mm10-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'mm10', u'species': u'Mus_musculus'}}}} 


def test_print_summary():
    """
    Test that the print summary function correctly handels no matches, some matches, etc.
    """
    pytest_enable_socket()
    
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'hg38 cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg38-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'10-Aug-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg38 reference genome from UCSC. This version includes the latest patch, patch 12. (url:http://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/p12/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The GRCh37 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'25-May-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg19 reference genome from UCSC. This version includes the latest patch, patch 13. (http://hgdownload.soe.ucsc.edu/goldenPath/hg19/hg19Patch13/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'ESP variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'18-Nov-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-phastcons': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'09-Feb-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-phastcons-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'phastCons', u'conservation'], u'summary': u'phastCons scores for MSA of 99 genomes to hg19', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## test that no results exits correclty
    search_term = ["Failed Search"]
    matches = []
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.print_summary(search_term,json_dict,matches,{},[])
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1


    ## Test matches print out and function returns true
    search_term = ["gaps"]
    matches = ["hg19-gaps"]
    installed_pkgs = set()
    installed_paths = []
    assert search.print_summary(search_term,json_dict,matches,installed_pkgs,installed_paths) == True

    ## Test that a match that does not exists in the json_dict is handeled correctly
    search_term = ["gaps"]
    matches = ["hg19-gaps", "bad-package"]
    installed_pkgs = set()
    installed_paths = []
    assert search.print_summary(search_term,json_dict,matches,installed_pkgs,installed_paths) == True


def test_main_search():
    """
    Test the main search method with different argument parameters
    """
    pytest_enable_socket()
            
    parser = ()

    ## Test a general search 
    args = Namespace(channel='genomics', command='search', display_number=5, genome_build=[], match_score='75', search_type = "both", search_term=['reference'], species=[])
    assert search.search(parser,args)

    ## Test a general search with combined-only search type 
    args = Namespace(channel='genomics', command='search', display_number=5, genome_build=[], match_score='75', search_type = "combined-only", search_term=['reference','genome'], species=[])
    assert search.search(parser,args)

    ## Test a general search with non-combined-only search type 
    args = Namespace(channel='genomics', command='search', display_number=5, genome_build=[], match_score='75', search_type = "non-combined-only", search_term=['reference','genome'], species=[])
    assert search.search(parser,args)

    ## Test search with genome build 
    args = Namespace(channel='genomics', command='search', display_number=5, genome_build=["GRCh37"], match_score='75', search_type = "both", search_term=['reference'], species=[])
    assert search.search(parser,args) 

    ## Test search with species 
    args = Namespace(channel='genomics', command='search', display_number=5, genome_build=[], match_score='75', search_type = "both", search_term=['reference'], species=["Homo_sapiens"])
    assert search.search(parser,args) 

    ## Test with genome build and species
    args = Namespace(channel='genomics', command='search', display_number=5, genome_build=["GRCh37"], match_score='75', search_type = "both", search_term=['reference'], species=["Homo_sapiens"])
    assert search.search(parser,args) 

    ## Test with genome build and species in search terms
    args = Namespace(channel='genomics', command='search', display_number=5, genome_build=[], match_score='75', search_type = "both", search_term=['reference','grch37','homo_sapiens'], species=[])
    assert search.search(parser,args) 

    ## Test with genome build in search terms
    temp_stdout = StringIO()
    args = Namespace(channel='genomics', command='search', display_number=100, genome_build=[], match_score='75', search_type = "both", search_term=['reference','grch37'], species=[])
    with redirect_stdout(temp_stdout):
        search.search(parser,args) 
    output = temp_stdout.getvalue().strip() 
    assert "grch37" in output
    assert "\033[1m" + "Genome Build:" + "\033[0m GRCh37" in output
    assert "hg19-" not in output
    assert "\033[1m" + "Genome Build:" + "\033[0m hg19" not in output
    assert "hg38" not in output
    assert "grch38" not in output
    assert "Homo_sapiens" in output
    assert "Mus_musculus" not in output
    assert "Drosophila_melanogaster" not in output
    assert "grch37-reference-genome-ensembl-v1" in output

    ## Test with species in search terms
    temp_stdout = StringIO()
    args = Namespace(channel='genomics', command='search', display_number=100, genome_build=[], match_score='75', search_type = "both", search_term=['reference','homo_sapiens'], species=[])
    with redirect_stdout(temp_stdout):
        search.search(parser,args) 
    output = temp_stdout.getvalue().strip() 
    assert "grch37" in output
    assert "hg19" in output
    assert "\033[1m" + "Genome Build:" + "\033[0m GRCh37" in output
    assert "hg19-" in output
    assert "\033[1m" + "Genome Build:" + "\033[0m hg19" in output
    assert "hg38" in output
    assert "\033[1m" + "Genome Build:" + "\033[0m hg38" in output
    assert "grch38" in output
    assert "\033[1m" + "Genome Build:" + "\033[0m GRCh38" in output
    assert "Homo_sapiens" in output
    assert "\033[1m" + "Species:" + "\033[0m Homo_sapiens" in output
    assert "Mus_musculus" not in output
    assert "\033[1m" + "Species:" + "\033[0m Mus_musculus" not in output
    assert "Drosophila_melanogaster" not in output
    assert "\033[1m" + "Species:" + "\033[0m Drosophila_melanogaster" not in output

    ## Test with genome build and species in search terms
    ## NOTE: genome build should take precedence over species. So only genome build should be displayed, not all species
    temp_stdout = StringIO()
    args = Namespace(channel='genomics', command='search', display_number=100, genome_build=[], match_score='75', search_type = "both", search_term=['reference','grch37','homo_sapines'], species=[])
    with redirect_stdout(temp_stdout):
        search.search(parser,args) 
    output = temp_stdout.getvalue().strip() 
    assert "grch37" in output
    assert "\033[1m" + "Genome Build:" + "\033[0m hg19" not in output
    assert "hg38" not in output
    assert "\033[1m" + "Genome Build:" + "\033[0m hg38" not in output
    assert "\033[1m" + "Genome Build:" + "\033[0m GRCh38" not in output
    assert "\033[1m" + "Species:" + "\033[0m Homo_sapiens" in output
    assert "Mus_musculus" not in output
    assert "\033[1m" + "Species:" + "\033[0m Mus_musculus" not in output
    assert "Drosophila_melanogaster" not in output
    assert "\033[1m" + "Species:" + "\033[0m Drosophila_melanogaster" not in output
    assert "grch37-reference-genome-ensembl-v1" in output

    ## Test with genome build and other species in search terms
    ## NOTE: genome build should take precedence over species. If genome build not for provided species, species will remain 
    temp_stdout = StringIO()
    args = Namespace(channel='genomics', command='search', display_number=100, genome_build=[], match_score='75', search_type = "both", search_term=['reference','grch37','homo_sapines','Mus_musculus'], species=[])
    with redirect_stdout(temp_stdout):
        search.search(parser,args) 
    output = temp_stdout.getvalue().strip() 
    assert "grch37" in output
    assert "\033[1m" + "Genome Build:" + "\033[0m GRCh37" in output
    assert "hg19-" not in output
    assert "\033[1m" + "Genome Build:" + "\033[0m hg19" not in output
    assert "hg38-" not in output
    assert "\033[1m" + "Genome Build:" + "\033[0m hg38" not in output
    assert "grch38-" not in output
    assert "\033[1m" + "Genome Build:" + "\033[0m GRCh38" not in output
    assert "Homo_sapiens" in output
    assert "Mus_musculus" in output
    assert "mm10" in output
    assert "mm10-reference-ucsc-v1" in output
    assert "\033[1m" + "Species:" + "\033[0m Mus_musculus" in output
    assert "Drosophila_melanogaster" not in output
    assert "\033[1m" + "Species:" + "\033[0m Drosophila_melanogaster" not in output
    assert "grch37-reference-genome-ensembl-v1" in output


    ## Test that Approximate data file sizes, final file list, and other tag info are reported  
    ## Test also that the recipe name list is added at the end of the detailed output
    temp_stdout = StringIO()
    args = Namespace(channel='genomics', command='search', display_number=1, genome_build=[], match_score='75', search_type = "both", search_term=['grch37','gene-features'], species=[])
    with redirect_stdout(temp_stdout):
        search.search(parser,args) 
    output = temp_stdout.getvalue().strip() 
    assert "\033[1m" + "Summary:" + "\033[0m" in output
    assert "\033[1m" + "Species:" + "\033[0m" in output
    assert "\033[1m" + "Genome Build:" + "\033[0m" in output
    assert "\033[1m" + "Keywords:" + "\033[0m" in output
    assert "\033[1m" + "Data Provider:" + "\033[0m" in output
    assert "\033[1m" + "Data Version:" + "\033[0m" in output
    assert "\033[1m" + "File type(s):" + "\033[0m" in output
    assert "\033[1m" + "Data file coordinate base:" + "\033[0m" in output
    assert "\033[1m" + "Included Data Files:" + "\033[0m" in output
    assert "\033[1m" + "Approximate Data File Sizes:" + "\033[0m" in output
    assert "\033[1mPackage Name Results\033[0m" in output
    assert "NOTE: Name order matches order of packages in detailed section above" in output
    assert "\033[1m>>> Scroll up to see package details and install info <<<\033[0m" in output



    ## Test that a data file path is given if the package is installed
    temp_stdout = StringIO()
    args = Namespace(channel='genomics', command='search', display_number=5, genome_build=["hg19"], match_score='75', search_type = "both", search_term=['reference','gaps','hg19-gaps-ucsc-v1'], species=[])
    search.search(parser,args) 
    with redirect_stdout(temp_stdout):
        search.search(parser,args) 
    output = temp_stdout.getvalue().strip() 
    assert "This package is already installed on your system" in str(output)
    assert "You can find the installed data files here" in str(output)
    try:
        uninstall_hg19_gaps_ucsc_v1
    except:
        pass

    ## Test bad term search 
    args = Namespace(channel='genomics', command='search', display_number=5, genome_build=[], match_score='75', search_type = "both", search_term=['zzzzzzzzzzzzzzzzzzzzzzz'], species=[])
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.search(parser,args) 
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1



