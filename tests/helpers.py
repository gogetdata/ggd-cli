from textwrap import dedent
import yaml
import os
import subprocess as sp
import sys
import pytest
import yaml
import tempfile
import requests
import glob
from ggd import install, uninstall 
from future.utils import iteritems


#--------------------------------------------------------------------------------------------------
## Helper Functions
#--------------------------------------------------------------------------------------------------

def install_hg19_gaps_ucsc_v1():
    """ 
    Method to install the hg19-gaps-ucsc-v1 data package using ggd prior to testing. Also test if installation completed 

    Returns the version of the hg19-gaps-ucsc-v1 ggd packge installed
    """

    name = "hg19-gaps-ucsc-v1"
    try:
        assert sp.check_call(["ggd", "install", name])
    except Exception as e:
        print("Assertion failed")
        jdict = install.check_ggd_recipe(name,"genomics")
        species =  jdict["packages"][name]["identifiers"]["species"] == "Homo_sapiens"
        genome_build =  jdict["packages"][name]["identifiers"]["genome-build"] == "hg19"
        version = jdict["packages"][name]["version"]
        ggd_jdict = {"packages":{name:{"identifiers":{"species":species,"genome-build":genome_build},"version":version}}}
        uninstall.check_for_installation([name],ggd_jdict) ## .uninstall method to remove extra ggd files
        ## Exit
        sys.exit(1)  

    jdict = install.check_ggd_recipe(name,"genomics")
    version = jdict["packages"][name]["version"]
    return(version)


def uninstall_hg19_gaps_ucsc_v1():
    """ 
    Method to uninstall the hg19-gaps-ucsc-v1 data package using ggd prior to testing. Also test if uninstallation completed 

    Returns the version of the hg19-gaps-ucsc-v1 ggd packge uninstalled
    """

    name = "hg19-gaps-ucsc-v1"
    try:
        assert sp.check_call(["ggd", "uninstall", name]) == 0
    except Exception as e:
        print("Assertion failed")
        jdict = install.check_ggd_recipe(name,"genomics")
        species =  jdict["packages"][name]["identifiers"]["species"] == "Homo_sapiens"
        genome_build =  jdict["packages"][name]["identifiers"]["genome-build"] == "hg19"
        version = jdict["packages"][name]["version"]
        ggd_jdict = {"packages":{name:{"identifiers":{"species":species,"genome-build":genome_build},"version":version}}}
        uninstall.check_for_installation([name],ggd_jdict) ## .uninstall method to remove extra ggd files
        ## Exit
        sys.exit(1)  
    #assert sp.check_call(["ggd", "uninstall", name]) == 0

    jdict = install.check_ggd_recipe(name,"genomics")
    version = jdict["packages"][name]["version"]
    return(version)


class CreateRecipe(object):
    def __init__(self, data, from_string=False):
        """
        
        
        Adapted from bioconda-utils/tests/helpers.Recipe().
        Create a directory of meta.yaml files for a hypothetical ggd recipe
        Test cases can use this class to create yaml files and test them.

        Top level = recipe
        Next level = met.yaml 
        Following string is the yaml info

        Example, this YAML file::
            recipe:
              meta.yaml: |
                build:
                  binary_relocation: false
                  detect_binary_files_with_prefix: false
                  noarch: generic
                  number: 1
                extra:
                  authors: me
                package:
                  name: hg19-gaps
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
                  summary: Assembly gaps from USCS
                  tags:
                    data-version: 27-Apr-2009
                    ggd-channel: genomics

        Parameters
        ----------
        data : str
            If `from_string` is False, this is a filename relative to this
            module's file. If `from_string` is True, then use the contents of
            the string directly.
        from_string : bool
        Useful attributes:
        * recipes: a dict mapping recipe names to parsed meta.yaml contents
        * basedir: the tempdir containing all recipes. Many bioconda-utils
                   functions need the "recipes dir"; that's this basedir.
        * recipe_dir: a dict mapping recipe names to newly-created recipe
                   dirs. These are full paths to subdirs in `basedir`.
        """

        if from_string:
            self.data = dedent(data)
            self.recipes = yaml.safe_load(data)
        else:
            self.data = os.path.join(os.path.dirname(__file__), data)
            self.recipes = yaml.safe_load(open(self.data))

    def write_recipes(self):
        basedir = tempfile.mkdtemp()
        self.recipe_dirs = {}
        for name, recipe in self.recipes.items():
            rdir = os.path.join(basedir, name)
            os.makedirs(rdir)
            self.recipe_dirs[name] = rdir
            for key, value in recipe.items():
                with open(os.path.join(rdir, key), 'w') as fout:
                    fout.write(value)
        self.basedir = basedir

    def write_nested_recipes(self):
        """Method to create a nested level "recipe" or directory path with files in the base dir

        - top level dirs should have "dir" in the name
        - base level dirs should NOT have a "dir" in the name
            + a base dir is any dir that will have files in it
        
        Example:

            Toplevel_dir:
                nextlevel_dir:
                    anotherlevel_dir:
                        baselevel: 
                            first_file: |
                                Text in the first file 
                                .
                                .
                                .

                            second_file: |
                                Text in the second file
                                .
                                .
                                .
        Results:
        ++++++++
        The dict returned will be: key = dir-name, value = dir path
            nested dirs will be seperated with a "/". 
            For the example above, to get the base dir the key would be: "Toplevel_dir/nextlevel_dir/anotherlevel_dir/baselevel"
        """

        basedir = tempfile.mkdtemp()
        self.recipe_dirs = {}

        def nested_recipe(recipe_list,base_dir,base_dir_name=""):

            for name, recipe in recipe_list.items():
                rdir = os.path.join(base_dir, name)
                os.makedirs(rdir)
                updated_name = base_dir_name + "/" + name if base_dir_name != "" else name 
                self.recipe_dirs[updated_name] = rdir
                if "dir" in name:
                    nested_recipe(recipe,rdir,updated_name)
                else:
                    for key, value in recipe.items():
                        with open(os.path.join(rdir, key), 'w') as fout:
                            fout.write(value)
            self.basedir = basedir

        nested_recipe(self.recipes,basedir)


