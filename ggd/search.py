#-------------------------------------------------------------------------------------------------------------
## Import Statements
#-------------------------------------------------------------------------------------------------------------
from __future__ import print_function
import sys 
import os
import argparse
import glob
import json
import requests
import traceback
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from .utils import get_species
from .utils import get_ggd_channels
from .utils import get_channeldata_url

SPECIES_LIST = get_species(update_repo=False)
CHANNEL_LIST = [x.encode('ascii') for x in get_ggd_channels()]

#-------------------------------------------------------------------------------------------------------------
## Argument Parser
#-------------------------------------------------------------------------------------------------------------
def add_search(p):
    c = p.add_parser("search", help="Search for a data recipe stored in ggd")
    c.add_argument("-t", "--term", nargs="+", required=True, help="**Required** The term(s) to search for. Multiple terms can be used. Example: '-t reference genome'")
    c.add_argument("-g", "--genome_build", help="(Optional) The genome build of the desired recipe")
    c.add_argument("-s", "--species", help="(Optional) The species for the desired recipe", choices=SPECIES_LIST)
    c.add_argument("-k", "--keyword", nargs="+", help="(Optional) Keyword(s) the are used to describe the recipe. Multiple keywords can be used. Example: '-k ref reference genome'")
    c.add_argument("-m", "--match_score", default="50", help="(Optional) A score between 0 and 100 to use percent match between the search term(s) and the ggd-recipes")
    c.add_argument("-c", "--channel", help="(Optional) The ggd channel to search. (Default = genomics)", choices=[x.decode('ascii') for x in CHANNEL_LIST],
                    default="genomics")
    c.set_defaults(func=search)


#-------------------------------------------------------------------------------------------------------------
## Functions/Methods
#-------------------------------------------------------------------------------------------------------------

def load_json(jfile):
    """Method to load a json file into a dictionary

    load_json
    =========
    Method to load a json file 

    Parameters:
    ---------
    1) jfile: The path to the json file

    Returns:
    1) A dictionary of a json object 
    """

    with open(jfile) as jsonFile:
       return(json.load(jsonFile))


def load_json_from_url(json_url):
    """Method to load a json file from a url

    load_json_from_url
    ==================
    Method to load a json file  from a url. Uses the requests module 
     to get the json file from the url.
   
    Parameters:
    ---------
    1) json_url: The url to the json path
   
    Returns:
    ++++++++
    1) A dictionary of a json object 
    """

    try:
        return(requests.get(json_url).json())
    except ValueError as e:
        sys.stderr.write("\n\t-> Error in loading json frile from url")
        sys.stderr.write("\n\t-> Invalid URL")
        sys.stderr.write("\n\t\t-> URL: %s\n" %json_url)
        sys.stderr.write(str(e))
        sys.stderr.write(traceback.format_exc())
        sys.exit(1)


def search_packages(jsonDict,searchTerm):
    """Method to search for ggd packages in the ggd channeldata.json metadata file based on user provided search terms

    search_packages
    ===============
    Method to search for ggd packages/recipes 
     contaniing specific search terms 

    Parameters:
    ---------
    1) jsonDict: A json file loaded into a dictionary. (The file to search)
                  the load_json_from_url() method creates the dictionary 
    2) searchTerm: A term or list of terms representing package names to search for

    Returns:
    ++++++++
    1) A list of each packages within the json dictionary, and the match score for each. 
        The match score is between 0 and 100, representing the percent match 
    """

    packages = jsonDict["packages"].keys()
    matchList = process.extract(searchTerm,packages,limit=10000) 
    return(matchList)


def filter_by_score(filterScore,matchList):
    """Method to filter search results by a match/filter score.

    filter_by_score
    ==============
    Method used to filter the match scored package list based on a match score.
     Any packages at or above the match score will be included in the final set
     Match/filter score is set to a default of 50, but can be adjusted by the user.

    Parameters:
    ----------
    1) filterScore: The match score to filter the recipes by
    2) matchList: The list of recipes with match scores

    Returns:
    ++++++++
    1) a new list of recipes filtered by the match score
    """
    newMatchList = [x for x in matchList if x[1] >= int(filterScore)]
    return(newMatchList)


def filter_by_identifiers(iden_key,matchList,jsonDict,filterTerm):
    """Method to filter the results based of an identifier field for the certain package.

    filter_by_identifiers
    =====================
    A method used to filter the list of recipes by information in the 
     identifiers field in the channeldata.json file

    Parameters:
    ----------
    1) iden_key: The identifiers key. Example = genome-build
    2) matchList: The list of recipes with match scores 
    3) jsonDict: The json dictionary craeted from laod_json()
    4) filterTerm: The term to filter by. Example: Homo_sapiens

    Returns:
    ++++++++
    1) A filtered list of pacakges
    """

    tempDict = {}
    tempSet = set()
    if len(matchList) < 1:
        print("\n\t---------------------------------------------\n\t|  No recipes to filter using '%s' | \n\t---------------------------------------------" %filterTerm)
        sys.exit()
    for key in matchList:
        if iden_key in jsonDict["packages"][key[0]]["identifiers"]:
            identifierTerm  = jsonDict["packages"][key[0]]["identifiers"][iden_key] 
            tempSet.add(identifierTerm)
            if identifierTerm in tempDict:
                tempDict[identifierTerm].append(key)
            else:
                tempDict[identifierTerm] = [key]
    if len(tempSet) > 0:
        filteredList = process.extract(filterTerm,tempSet,limit=100) 
        if filteredList[0][1] > 85: ## Match score greater than 85%
            return(tempDict[filteredList[0][0]])

    ## If unable to return a filtered set return the original match list
    print("\n-> Unable to filter recieps using: '%s'" %filterTerm)
    print("\tThe un-filtered list will be used\n")
    if iden_key == "species":
        print("\tAvaiable species terms = %s" %SPECIES_LIST)
    return(matchList)


def filter_by_keywords(matchList,jsonDict,filterTerm):
    """Method to filter search result based off keywords added to the ggd data package

    filter_by_keywords
    =====================
    A method used to filter the list of recipes by information in the 
     keywords field in the channeldata.json file

    Parameters:
    ----------
    1) matchList: The list of recipes with match scores 
    2) jsonDict: The json dictionary craeted from laod_json()
    3) filterTerm: The term to filter by. Example: regions

    Returns:
    ++++++++
    1) A filtered list of pacakges
    """

    tempDict = {}
    tempSet = set()
    if len(matchList) < 1:
        print("\n\t---------------------------------------------\n\t|  No recipes to filter using '%s' | \n\t---------------------------------------------" %filterTerm)
        sys.exit()
    for key in matchList:
        identifierTerm  = jsonDict["packages"][key[0]]["keywords"] 
        for keyword in identifierTerm:
            tempSet.add(keyword)
            if keyword in tempDict:
                tempDict[keyword].append(key)
            else:
                tempDict[keyword] = [key]
    filteredList = process.extract(filterTerm,tempSet,limit=100) 
    if filteredList[0][1] > 65: ## Match score greater than 65%
        return(tempDict[filteredList[0][0]])
    else:
        print("\n-> Unable to filter recieps using: '%s'" %filterTerm)
        print("\tThe un-filtered list will be used\n")
        return(matchList)


def print_summary(searchTerms,jsonDict,matchList):
    """ Method to print the summary/results of the search

    print_summary
    ============
    Method used to print out the final set of searched packages

    Parameters:
    ---------
    1) jsonDict: The json dictionary from the load_json() method
    2) matchList: The filtered and final set of searched recipes

    Returns:
    +++++++
    1) True if print summary printed out successfully
    """

    if len(matchList) < 1:
        print("\n\tNo results for %s. Update your search term and try again" %searchTerms)
        sys.exit()
    for key in matchList:
        if key[0] in jsonDict["packages"]:
            print("\n\n", key[0])
            if "summary" in jsonDict["packages"][key[0]] and jsonDict["packages"][key[0]]["summary"]:
                print("\tSummary:", jsonDict["packages"][key[0]]["summary"])
            if "identifiers" in jsonDict["packages"][key[0]] and jsonDict["packages"][key[0]]["identifiers"]:
                print("\tSpecies:", jsonDict["packages"][key[0]]["identifiers"]["species"])
                print("\tGenome Build:", jsonDict["packages"][key[0]]["identifiers"]["genome-build"])
            if "keywords" in jsonDict["packages"][key[0]] and jsonDict["packages"][key[0]]["keywords"]: 
                print("\tKeywords:", ", ".join(jsonDict["packages"][key[0]]["keywords"]))
            if "tags" in jsonDict["packages"][key[0]] and jsonDict["packages"][key[0]]["tags"]:
                if "data-version" in jsonDict["packages"][key[0]]["tags"]:
                    print("\tData Version:", jsonDict["packages"][key[0]]["tags"]["data-version"])
                if "cache" in jsonDict["packages"][key[0]]["tags"]:
                    print("\tCached:", jsonDict["packages"][key[0]]["tags"]["cached"])
            print("\n\tTo install run:\n\t\tggd install %s" %key[0])
    
    return(True)


def search(parser, args):
    """Main method for ggd search. 

    search
    =====
    Main method for running a recipe/package search

    Parameters:
    ----------
    1) parser  
    2) args
    """

    ## load the channeldata.json file
    jDict = load_json_from_url(get_channeldata_url(args.channel))
    #jDict = load_json(CHANNEL_DATA)
    matchResults = search_packages(jDict,str(args.term))

    ## extra filtering 
    matchResults = filter_by_score(args.match_score,matchResults)
    if args.genome_build:
        matchResults = filter_by_identifiers("genome-build",matchResults,jDict,args.genome_build)
    if args.species:
        get_species(update_repo=True) ## update the local repo.
        matchResults = filter_by_identifiers("species",matchResults,jDict,args.species)
    if args.keyword:
        matchResults = filter_by_keywords(matchResults,jDict,str(args.keyword))

    ## Print search results
    return(print_summary(args.term,jDict,matchResults))
    

