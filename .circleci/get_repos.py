from __future__ import print_function
import os
import sys
import subprocess as sp
import pytest
import yaml
import requests
import argparse
import re
from ggd import utils



#---------------------------------------------------------------------
## Clone repos
#---------------------------------------------------------------------

## Update local genomic metadata files
utils.update_genome_metadata_files()

##Update local channeldata.json metadata file
utils.update_channel_data_files("genomics")

## Get species
utils.get_species(update_files=True)

## get channels
channels = utils.get_ggd_channels()

## get channel data
for x in channels:
    utils.get_channel_data(x)




