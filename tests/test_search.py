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
from argparse import Namespace
from argparse import ArgumentParser

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
    bad_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/channeldata/NOTAREALCHANNEL.channeldata.json"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.load_json_from_url(bad_url)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("1") ## Check that the exit code is 1


def test_load_json_from_url_goodurl():
    """
    test if a good url does load
    """
    good_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/channeldata/genomics/channeldata.json"
    assert search.load_json_from_url(good_url)


def test_search_package_madeup_package():
    """
    Test the search_pacakge method to see if it properly identifies a madeup package
    """
    name = "Madeup-package"
    search_term = "madeup"
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Madeup_package': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/Madeup_package-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}}

    ## Default match score >= 50
    assert search.search_packages(json_dict,search_term)[0][1] >= 50

    search_term = "made package"
    ## Default match score >= 50
    assert search.search_packages(json_dict,search_term)[0][1] >= 50


def test_search_package_madeup_package_badsearchterm():
    """
    Test the search_pacakge method to see if it returns no package based on bad search terms
    """
    name = "Madeup-package"
    search_term = "NO"
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': {u'Madeup_package': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/Madeup_package-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}}}

    ## Default match score >= 50
    assert search.search_packages(json_dict,search_term)[0][1] < 50
   
    search_term = "BAD SEARCH"
    ## Default match score >= 50
    assert search.search_packages(json_dict,search_term)[0][1] < 50


def filter_score_test(score,matchlist,results):
    """
    Helper script for the test_filter_by_score() function. Runs the assert test for a speciifc set of matches, results, and scores
    """
    for match in matchlist:
        if match[1] >= score:
            assert match in results
        else:
            assert match not in results


def test_filter_by_score():
    """
    test the filter_by_score function. Based off a specific filter score test that the appropriate packages are returned
    """
    matches = [("Zero-package", 0), ("twenty-pacakge", 20), ("fourty-five, package", 45),("hg19-gaps", 50), 
                ("hg19-repeatmasker", 55), ("hg19-simplerepeats", 60), ("hg19-phastcons", 65), ("hg19-pfam-domains", 70), 
                ("hg38-gaps", 75), ("hg38-repeatmasker", 80), ("hg38-simplerepeats", 85), ("hg38-phastcons", 90), 
                ("hg38-pfam-domains", 95), ("grch37-reference-genome", 100)] 

    ## Check a filter score of 0
    filterscore = 0
    filter_score_test(filterscore,matches,search.filter_by_score(filterscore, matches))

    filterscore = 20
    filter_score_test(filterscore,matches,search.filter_by_score(filterscore, matches))

    filterscore = 45
    filter_score_test(filterscore,matches,search.filter_by_score(filterscore, matches))

    filterscore = 50
    filter_score_test(filterscore,matches,search.filter_by_score(filterscore, matches))

    filterscore = 75
    filter_score_test(filterscore,matches,search.filter_by_score(filterscore, matches))

    filterscore = 85
    filter_score_test(filterscore,matches,search.filter_by_score(filterscore, matches))

    filterscore = 100
    filter_score_test(filterscore,matches,search.filter_by_score(filterscore, matches))


def test_filter_by_identifiers_genome_build():
    
    key = "genome-build"
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
    matches = []
    filter_term = "hg19"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.filter_by_identifiers(key,matches,json_dict,filter_term)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1

    ## Test filter based on "hg19" genome build
    matches = [("hg19-repeatmasker", 80), ("hg38-repeatmasker", 80), ("hg19-simplerepeats", 75), ("hg38-simplerepeats", 75)]
    filter_term = "hg19"
    assert search.filter_by_identifiers(key,matches,json_dict,filter_term) == [("hg19-repeatmasker", 80), ("hg19-simplerepeats", 75)]

    ## Test filter based on "hg38" genome build
    matches = [("hg19-repeatmasker", 80), ("hg38-repeatmasker", 80), ("hg19-simplerepeats", 75), ("hg38-simplerepeats", 75)]
    filter_term = "hg38"
    assert search.filter_by_identifiers(key,matches,json_dict,filter_term) == [("hg38-repeatmasker", 80), ("hg38-simplerepeats", 75)]

    ## Test unable to filter based on bad genome build
    matches = [("hg19-repeatmasker", 80), ("hg38-repeatmasker", 80), ("hg19-simplerepeats", 75), ("hg38-simplerepeats", 75)]
    filter_term = "Bad-genome-build"
    ## Assert that if a the filter term was unable to filter anything the original list is returned
    assert search.filter_by_identifiers(key,matches,json_dict,filter_term) == matches


def test_filter_by_identifiers_bad_identifier():
    """
    Test that the filter_by_idenfiiers function correclty processes a bad identifier key passed to the function 
    """
    key = "Bad-Identifier"
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
    matches = []
    filter_term = "hg19"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.filter_by_identifiers(key,matches,json_dict,filter_term)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1

    ## Test filter identifiers returns original list if the identifiers key is not in the identifiers dictionary
    matches = [("hg19-repeatmasker", 80), ("hg38-repeatmasker", 80), ("hg19-simplerepeats", 75), ("hg38-simplerepeats", 75)]
    filter_term = "hg19"
    assert search.filter_by_identifiers(key,matches,json_dict,filter_term) == matches


def test_filter_by_identifiers_species():
    """
    Test the filter by idenfiiers function using species 
    """
    key = "species"
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
    matches = []
    filter_term = "Homo_sapiens"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.filter_by_identifiers(key,matches,json_dict,filter_term)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1

    ## Set matches list
    matches = [("hg19-gaps", 80), ("dm3-cpg-islands", 75), ("mm10-repeatmasker", 93), ("hg19-pfam-domains-ucsc", 87), 
                ("dm6-reference-genome-ucsc", 68), ("mm9-reference-genome-ensembl", 73), ("grch38-reference-genome-ensembl", 94),
                ("dm3-reference-genome-ucsc", 61), ("mm10-esp-variants", 77), ("hg19-cpg-islands", 89), ("dm6-pfam-domains-ucsc", 65),
                ("mm9-simplerepeats", 58), ("hg19-repeatmasker", 54), ("dm3-phastcons", 90), ("mm10-reference-genome", 77),
                ("hg38-simplerepeats", 98)]

    ## Test filter based on "Homo_sapiens" species
    filter_term = "Homo_sapiens"
    assert search.filter_by_identifiers(key,matches,json_dict,filter_term) == [("hg19-gaps", 80), 
                                                                                ("hg19-pfam-domains-ucsc", 87), 
                                                                                ("grch38-reference-genome-ensembl", 94),
                                                                                ("hg19-cpg-islands", 89), 
                                                                                ("hg19-repeatmasker", 54),
                                                                                ("hg38-simplerepeats", 98)]
    ## Test filter based on "Drosophila_melanogaster" species
    filter_term = "Drosophila_melanogaster"
    assert search.filter_by_identifiers(key,matches,json_dict,filter_term) == [("dm3-cpg-islands", 75), 
                                                                                ("dm6-reference-genome-ucsc", 68), 
                                                                                ("dm3-reference-genome-ucsc", 61), 
                                                                                ("dm6-pfam-domains-ucsc", 65),
                                                                                ("dm3-phastcons", 90)] 

    ## Test filter based on "Mus_musculus" species
    filter_term = "Mus_musculus"
    assert search.filter_by_identifiers(key,matches,json_dict,filter_term) == [("mm10-repeatmasker", 93), 
                                                                                ("mm9-reference-genome-ensembl", 73), 
                                                                                ("mm10-esp-variants", 77), 
                                                                                ("mm9-simplerepeats", 58), 
                                                                                ("mm10-reference-genome", 77)]
    ## Test unable to filter based on bad species
    filter_term = "Bad-species"
    ## Assert that if a the filter term was unable to filter anything the original list is returned
    assert search.filter_by_identifiers(key,matches,json_dict,filter_term) == matches


def test_filter_by_keywords():
    """
    Test the filter_by_keyword function to properly filter recipe based off keywords associated with packages
    """

    ## create json dict
    json_dict = {u'channeldata_version': 1, u'subdirs': [u'noarch'], u'packages': 
                    {u'hg19-gaps': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-gaps-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'gaps', u'region'], u'summary': u'Assembly gaps from USCS', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'11-Mar-2019'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'Islands', u'region'], u'summary': u'hg38 cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg38-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'16-Apr-2017'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'10-Aug-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg38 reference genome from UCSC. This version includes the latest patch, patch 12. (url:http://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/p12/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-75'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'Ensembl', u'Release75'], u'summary': u'The GRCh37 reference genome from Ensembl. Release 75. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'grch38-reference-genome-ensembl': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'Release-95'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch38-reference-genome-ensembl-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'Ensembl'], u'summary': u'The GRCh38 reference genome from Ensembl. Release 95. Primary Assembly file', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-reference-genome-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'25-May-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-reference-genome-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference', u'genome', u'UCSC'], u'summary': u'The hg19 reference genome from UCSC. This version includes the latest patch, patch 13. (http://hgdownload.soe.ucsc.edu/goldenPath/hg19/hg19Patch13/)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-esp-variants': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'ESP6500SI-V2'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-esp-variants-1-1.tar.bz2', u'pre_link': False, u'keywords': [u'ESP'], u'summary': u'ESP variants (More Info: http://evs.gs.washington.edu/EVS/#tabs-7)', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg19-cpg-islands': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-cpg-islands-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'CpG', u'Islands', u'region'], u'summary': u'cpg islands from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg38-pfam-domains-ucsc': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'18-Nov-2018'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-pfam-domains-ucsc-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'pfam', u'domains', u'protein', u'protein-domains', u'UCSC'], u'summary': u'Pfam domain annotation in bed12 format. (From UCSC)', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}, 
                    u'hg19-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-repeatmasker': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'27-Apr-2009'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-repeatmasker-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'rmsk', u'region'], u'summary': u'RepeatMasker track from UCSC', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'hg19-phastcons': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'09-Feb-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg19-phastcons-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'phastCons', u'conservation'], u'summary': u'phastCons scores for MSA of 99 genomes to hg19', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg19', u'species': u'Homo_sapiens'}}, 
                    u'grch37-reference-genome': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'phase2_reference'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/grch37-reference-genome-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'ref', u'reference'], u'summary': u'GRCh37 reference genome from 1000 genomes', u'text_prefix': False, u'identifiers': {u'genome-build': u'GRCh37', u'species': u'Homo_sapiens'}}, 
                    u'hg38-simplerepeats': {u'activate.d': False, u'version': u'1', u'tags': {u'cached': [u'uploaded_to_aws'], u'ggd-channel': u'genomics', u'data-version': u'06-Mar-2014'}, u'post_link': True, u'binary_prefix': False, u'run_exports': {}, u'pre_unlink': False, u'subdirs': [u'noarch'], u'deactivate.d': False, u'reference_package': u'noarch/hg38-simplerepeats-1-3.tar.bz2', u'pre_link': False, u'keywords': [u'simrep', u'regions'], u'summary': u'Simple repeats track from UCSC | name=sequence | score=alignment score | col 7 = period | col 8 = copy_num', u'text_prefix': False, u'identifiers': {u'genome-build': u'hg38', u'species': u'Homo_sapiens'}}}}

    ## Test empty match list
    matches = []
    filter_term = "region"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.filter_by_keywords(matches,json_dict,filter_term)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1

    ## Create match list
    matches = [("hg19-gaps", 90), ("hg38-cpg-islands", 88), ("hg38-repeatmasker", 77), ("hg19-pfam-domains-ucsc", 67), 
                ("hg38-reference-genome-ucsc", 64), ("grch37-reference-genome-ensembl", 65), ("grch38-reference-genome-ensembl", 74), 
                ("hg19-reference-genome-ucsc", 78), ("grch37-esp-variants", 68), ("hg19-cpg-islands", 59), ("hg38-pfam-domains-ucsc", 71),
                ("hg19-simplerepeats", 69), ("hg19-repeatmasker", 64), ("hg19-phastcons", 55), ("grch37-reference-genome", 94), 
                ("hg38-simplerepeats", 99)]

    ## Test single filter_term
    filter_term = "region"
    print(search.filter_by_keywords(matches,json_dict,filter_term))
    assert search.filter_by_keywords(matches,json_dict,filter_term) == [('hg19-gaps', 90), 
                                                                        ('hg38-cpg-islands', 88), 
                                                                        ('hg38-repeatmasker', 77), 
                                                                        ('hg19-cpg-islands', 59), 
                                                                        ('hg19-repeatmasker', 64)]
    ## Test mutliple filter_term
    filter_term = "CpG Islands"
    print(search.filter_by_keywords(matches,json_dict,filter_term))
    assert search.filter_by_keywords(matches,json_dict,filter_term) == [('hg38-cpg-islands', 88), ('hg19-cpg-islands', 59)] 

    ## Test bad filter term returns the original match list
    filter_term = "bad"
    assert search.filter_by_keywords(matches,json_dict,filter_term) == matches 


def test_print_summary():
    """
    Test that the print summary function correctly handels no matches, some matches, etc.
    """
    
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
    search_term = "Failed Search"
    matches = []
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.print_summary(search_term,json_dict,matches)
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1


    ## Test matches print out and function returns true
    search_term = "gaps"
    matches = [("hg19-gaps", 90)]
    assert search.print_summary(search_term,json_dict,matches) == True


    ## Test that a match that does not exists in the json_dict is handeled correctly
    search_term = "gaps"
    matches = [("hg19-gaps", 90), ("bad-package", 0)]
    assert search.print_summary(search_term,json_dict,matches) == True


def test_main_search():
    """
    Test the main search method with different argument parameters
    """
    parser = ()

    ## Test a general search 
    args = Namespace(channel='genomics', command='search', genome_build=None, keyword=None, match_score='50', species=None, term=['reference']) 
    assert search.search(parser,args) == search.search(parser,args) 

    ## Test search with genome build 
    args = Namespace(channel='genomics', command='search', genome_build="grch37", keyword=None, match_score='50', species=None, term=['reference']) 
    assert search.search(parser,args) 

    ## Test search with species 
    args = Namespace(channel='genomics', command='search', genome_build=None, keyword=None, match_score='50', species="Homo_sapiens", term=['reference']) 
    assert search.search(parser,args) 

    ## Test with genome build and species
    args = Namespace(channel='genomics', command='search', genome_build="grch37", keyword=None, match_score='50', species="Homo_sapiens", term=['reference']) 
    assert search.search(parser,args) 

    ## Test with a key word
    args = Namespace(channel='genomics', command='search', genome_build=None, keyword=["cpg"], match_score='50', species=None, term=['hg']) 
    assert search.search(parser,args) 

    ## Test with a key word and genome build
    args = Namespace(channel='genomics', command='search', genome_build="hg19", keyword=["cpg"], match_score='50', species=None, term=['hg']) 
    assert search.search(parser,args) 

    ## Test with a key word and genome build
    args = Namespace(channel='genomics', command='search', genome_build="hg19", keyword=["cpg"], match_score='50', species="Homo_sapiens", term=['hg']) 
    assert search.search(parser,args) 

    ## Test bad term search 
    args = Namespace(channel='genomics', command='search', genome_build=None, keyword=None, match_score='50', species=None, term=['zzzzzzzzzzzzzzzzzzzzzzz']) 
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.search(parser,args) 
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1

    ## Test bad term search with keyword  
    args = Namespace(channel='genomics', command='search', genome_build=None, keyword=["cpg"], match_score='50', species=None, term=['zzzzzzzzzzzzzzzzzzzzzzz']) 
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.search(parser,args) 
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1

    ## Test bad term search with genome build
    args = Namespace(channel='genomics', command='search', genome_build="hg19", keyword=["cpg"], match_score='50', species=None, term=['zzzzzzzzzzzzzzzzzzzzzzz']) 
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.search(parser,args) 
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    assert pytest_wrapped_e.match("") ## Check that the exit code is 1

    ## Test bad term search with species
    args = Namespace(channel='genomics', command='search', genome_build="hg19", keyword=["cpg"], match_score='50', species="Homo_sapiens", term=['zzzzzzzzzzzzzzzzzzzzzzz']) 
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        search.search(parser,args) 
    assert "SystemExit" in str(pytest_wrapped_e.exconly()) ## test that SystemExit was raised by sys.exit() 
    
