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
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from .utils import get_species
from .utils import get_ggd_channels
from .utils import get_channeldata_url

SPECIES_LIST = get_species()
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

# load_json
# =========
# Method to load a json file 
#
# Parameters:
# ---------
# 1) jfile: The path to the json file
#
# Returns:
# 1) A dictionary of a json object 
def load_json(jfile):
    with open(jfile) as jsonFile:
       return(json.load(jsonFile))


# load_json_from_url
# =========
# Method to load a json file  from a url. Uses the requests module 
#  to get the json file from the url.
#
# Parameters:
# ---------
# 1) json_url: The url to the json path
#
# Returns:
# 1) A dictionary of a json object 
def load_json_from_url(json_url):
	return(requests.get(json_url).json())


# search_packages
# ==============
# Method to search for ggd packages/recipes 
#  contaniing specific search terms 
#
# Parameters:
# ---------
# 1) jsonDict: A json file loaded into a dictionary. (The file to search)
#               the load_json() method creates the dictionary 
# 2) searchTerm: A term or list of terms representing package names to search for
#
# Returns:
# 1) A list of each packages within the json dictionary, and the match score for reach. 
#     The match score is between 0 and 100, representing the percent match 
def search_packages(jsonDict,searchTerm):
    packages = jsonDict["packages"].keys()
    matchList = process.extract(searchTerm,packages,limit=10000) 
    return(matchList)


# print_summary
# ============
# Method used to print out the final set of searched packages
#
# Parameters:
# ---------
# 1) jsonDict: The json dictionary from the load_json() method
# 2) matchList: The filtered and final set of searched recipes
def print_summary(searchTerms,jsonDict,matchList):
    if len(matchList) < 1:
        print("\n\tNo results for %s. Update your search term and try again" %searchTerms)
        sys.exit()
    for key in matchList:
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
    

# filter_by_score
# ==============
# Method used to filter the match scored package list based on a match score.
#  Any packages at or above the match score will be included in the final set
#
# Parameters:
# ----------
# 1) filterScore: The match score to filter the recipes by
# 2) matchList: The list of recipes with match scores
# 
# Returns:
# 1) a new list of recipes filtered by the match score
def filter_by_score(filterScore,matchList):
    newMatchList = [x for x in matchList if x[1] >= int(filterScore)]
    return(newMatchList)


# filter_by_identifiers
# =====================
# A method used to filter the list of recipes by information in the 
#  identifiers field in the channeldata.json file
#
# Parameters:
# ----------
# 1) iden_key: The identifiers key. Example = genome_build
# 2) matchList: The list of recipes with match scores 
# 3) jsonDict: The json dictionary craeted from laod_json()
# 4) filterTerm: The term to filter by. Example: Homo_sapiens
#
# Returns:
# 1) A filtered list of pacakges
def filter_by_identifiers(iden_key,matchList,jsonDict,filterTerm):
    tempDict = {}
    tempSet = set()
    if len(matchList) < 1:
        print("\n\t---------------------------------------------\n\t|  No recipes to filter using '%s' | \n\t---------------------------------------------" %filterTerm)
        sys.exit()
    for key in matchList:
        identifierTerm  = jsonDict["packages"][key[0]]["identifiers"][iden_key] 
        tempSet.add(identifierTerm)
        if identifierTerm in tempDict:
            tempDict[identifierTerm].append(key)
        else:
            tempDict[identifierTerm] = [key]
        
    filteredList = process.extract(filterTerm,tempSet,limit=100) 
    if filteredList[0][1] > 85: ## Match score greater than 85%
        return(tempDict[filteredList[0][0]])
    else:
        print("\n-> Unable to filter recieps using: '%s'" %filterTerm)
        print("\tThe un-filtered list will be used\n")
        if iden_key == "species":
			print("\tAvaiable species terms = %s" %SPECIES_LIST)
        return(matchList)


# filter_by_keywords
# =====================
# A method used to filter the list of recipes by information in the 
#  keywords field in the channeldata.json file
#
# Parameters:
# ----------
# 1) matchList: The list of recipes with match scores 
# 2) jsonDict: The json dictionary craeted from laod_json()
# 3) filterTerm: The term to filter by. Example: regions
#
# Returns:
# 1) A filtered list of pacakges
def filter_by_keywords(matchList,jsonDict,filterTerm):
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


# search
# =====
# Main method for running a recipe search
#
# Parameters:
# ----------
# 1) parser  
# 2) args
def search(parser, args):
	## load the channeldata.json file
	jDict = load_json_from_url(get_channeldata_url(args.channel))
	#jDict = load_json(CHANNEL_DATA)
	matchResults = search_packages(jDict,str(args.term))

	## extra filtering 
	matchResults = filter_by_score(args.match_score,matchResults)
	if args.genome_build:
		matchResults = filter_by_identifiers("genome-build",matchResults,jDict,args.genome_build)
	if args.species:
		matchResults = filter_by_identifiers("species",matchResults,jDict,args.species)
	if args.keyword:
		matchResults = filter_by_keywords(matchResults,jDict,str(args.keyword))

	## Print search results
	print_summary(args.term,jDict,matchResults)

