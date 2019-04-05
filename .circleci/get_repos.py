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

## Update local repo
utils.update_local_repo()

##Uupdate metadata repo
utils.update_metadata_local_repo()

## Get species
utils.get_species(update_repo=True)

## get channels
channels = utils.get_channels()

## get channel data
for x in channels:
    utils.get_channel_data(x)




