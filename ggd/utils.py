from __future__ import print_function
import os
import sys
import glob
from git import Repo
import subprocess as sp
import requests
import locale
import json
import shutil
import re
from pytest_socket import SocketBlockedError

LOCAL_REPO_DIR = os.getenv("GGD_LOCAL", os.path.expanduser("~/.config/ggd-info/"))
GENOME_METADATA_DIR = os.path.join(LOCAL_REPO_DIR,"genome_metadata")
CHANNEL_DATA_DIR = os.path.join(LOCAL_REPO_DIR,"channeldata")
RECIPE_REPO_DIR = os.path.join(LOCAL_REPO_DIR, "ggd-recipes")
GGD_CLI_REQUIREMENTS = "https://raw.githubusercontent.com/gogetdata/ggd-cli/master/requirements.txt"


def get_species(update_files=True,full_dict=False):
    """ Method to get available annotated species in the ggd repo

    get_species
    ===========
    This method is used to get a list of all available/annotated species in the 
    ggd repo. It returns a list of species

    Parameters:
    ----------
    1) update_files: Default=True. Update the local files before getting species
    2) full_dcit: Default=False. Get the full dictionary with keys as species and values as genome builds

    Returns:
    ++++++++
    1) If full_dict = False, a list of species
    or
    2) If full_dict = True, a dictionary with species as key and available genome builds as values 
    """

    if update_files and check_for_internet_connection():
        update_genome_metadata_files()       

    if full_dict:
        with open(os.path.join(GENOME_METADATA_DIR,"species_to_build.json"), "r") as f:
            return(json.load(f))
    else:
        with open(os.path.join(GENOME_METADATA_DIR,"species_to_build.json"), "r") as f:
            return(json.load(f).keys())


def get_ggd_channels():
    """Method used to get avaiable ggd channels
    
    get_ggd_channels
    ================
    This method is used to get all avaiable/created ggd conaa channels.
    This method will return a list of ggd conda channels.

    Run get_species() before running get_ggd_channels(). get_species triggers an update
     of local genomic metadata files
    """

    
    with open(os.path.join(GENOME_METADATA_DIR,"ggd_channels.json"), "r") as f:
        return(json.load(f)["channels"])


def get_channel_data(ggd_channel):
    """Method used to get channel meta data for a specific ggd channel

    get_channel_data
    ================
    This method is used to get the ggd channel's metadata json file. 

    Parameters:
    -----------
    1) ggd_channel: The ggd channel to get metadata for

    Returns:
    +++++++
    1) The file path to the metadata file for the specifc channel
    """

    if check_for_internet_connection():
        update_channel_data_files(ggd_channel)

    channeldata_path = os.path.join(CHANNEL_DATA_DIR,ggd_channel,"channeldata.json")
    return (channeldata_path)


def get_channeldata_url(ggd_channel):
    """Method used to get a url for the metadata json file for a specific ggd channel
    
    get_channeldata_url
    ===================
    This method is used to get a url for a specific metadata json file for a specific ggd conda channel

    Parameters:
    -----------
    1) ggd_channel: The ggd channel to get the metadata json file url for 

    Returns:
    ++++++++
    1) The url for the metadata file
    """

    ## Update local channel data file if internet connection availabe 
    if check_for_internet_connection():
        update_channel_data_files(ggd_channel)

    return(os.path.join("https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/channeldata", ggd_channel,
            "channeldata.json"))


def get_required_conda_version():
    """Method to get the conda version from the ggd-cli requirements file

    get_required_conda_version
    ==========================
    This method is used to get the required version for conda based on the version set in the 
     requiremetns file in ggd-cli. This version can be used to mantain the correct version while 
     using ggd

    Return:
    +++++++
    1) The required version if found, else -1
    """

    req = requests.get(GGD_CLI_REQUIREMENTS, stream=True)

    conda_version = -1
    for line in req.iter_lines():
        if "conda=" in str(line.decode()):
            conda_version = str(line.decode()).strip().split("=")[1]
    return(conda_version)


def check_output(args, **kwargs):
    """Method to get a byte converted string from a subprocess command """

    return _to_str(sp.check_output(args, **kwargs).strip())


def _to_str(s, enc=locale.getpreferredencoding()):
    """Method to convert a bytes into a string based on a local prefered encoding  

    _to_str
    =======
    This method is used to decode a bytes stream into a string based on the location/regional 
    preference. It returns the converted string. 
    """

    if isinstance(s, bytes):
        return s.decode(enc)
    return s
            

def get_builds(species):
    """
    Method to get the annotated/available genome builds for a species within ggd  

    Run get_species() before running get_builds(). get_species triggers an update
     of local genomic metadata files
    """

    if species == "*":
        with open(os.path.join(GENOME_METADATA_DIR,"build_to_species.json"), "r") as f:
            return(json.load(f).keys())
    else:
        ## Check if species is real
        with open(os.path.join(GENOME_METADATA_DIR,"species_to_build.json"), "r") as f:
            jdict = json.load(f)
            if species not in jdict.keys():
                sys.exit("'{s}' is not an available species in ggd. Please contact the ggd team to have it added".format(s=species))
            else:
                return(jdict[species])
        

def check_for_internet_connection(t=5):
    """
    Method to check if there is an internet connection or not
    """



    url='http://www.google.com/'
    timeout=t
    try:
        _ = requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        pass 
    except SocketBlockedError as e: 
        ## A pytest_socket SocketBlockedError. (This is raised when the network connection is disabled using pytest-socket plugin. 
        ## (For testing purposes)
        pass

    return False


def update_channel_data_files(channel):
    """Method to update the channel data metadata local files from the ggd-metadata repo
    
    update_channel_data_files
    =========================
    This method will download the json metadata json files for the channel data 

    Parameters:
    -----------
    1) channel: The channel to download for the channeldata
    """
    
    if channel in get_ggd_channels(): 

        if not os.path.isdir(LOCAL_REPO_DIR):
            os.makedirs(LOCAL_REPO_DIR)
        if not os.path.isdir(CHANNEL_DATA_DIR):
            os.makedirs(CHANNEL_DATA_DIR)

        channel_dir = os.path.join(CHANNEL_DATA_DIR,channel)
        if not os.path.isdir(channel_dir):
            os.makedirs(channel_dir)
        
        ## Dowload json file
        channeldata_url = os.path.join("https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/channeldata/",channel,"channeldata.json")

        channeldata_json = requests.get(channeldata_url).json()
        with open(os.path.join(channel_dir, "channeldata.json"), "w") as c:
            json.dump(channeldata_json,c)

    else: 
        sys.exit("The '{c}' channel is not a ggd conda channel".format(c=channel))
 
    return(True)


def update_genome_metadata_files():
    """Method to update the species and genome build, and ggd channel metadata files locally 

    update_genome_metadata_files
    ==========================================
    This method will download the json metadata species and genome-build files from ggd-metadata and store 
     in the LOCAL_REPO_DIR. 
    """

    if not os.path.isdir(LOCAL_REPO_DIR):
        os.makedirs(LOCAL_REPO_DIR)
    if not os.path.isdir(GENOME_METADATA_DIR):
        os.makedirs(GENOME_METADATA_DIR)

    ## Download the json files
    build_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/genome_metadata/build_to_species.json" 
    species_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/genome_metadata/species_to_build.json" 
    ggd_channels_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/genome_metadata/ggd_channels.json" 
    
    buildjson = requests.get(build_url).json()
    with open(os.path.join(GENOME_METADATA_DIR,"build_to_species.json"),"w") as b:
        json.dump(buildjson,b)

    speciesjson = requests.get(species_url).json()
    with open(os.path.join(GENOME_METADATA_DIR,"species_to_build.json"),"w") as s:
        json.dump(speciesjson,s)

    channeljson = requests.get(ggd_channels_url).json()
    with open(os.path.join(GENOME_METADATA_DIR,"ggd_channels.json"),"w") as s:
        json.dump(channeljson,s)

    return(True)


def update_installed_pkg_metadata(prefix=None,channel="ggd-genomcs",remove_old=True,exclude_pkg=None,add_package=None):
    """Method to update the local metadata file in a conda environment that contains information about the installed ggd packages

    update_installed_pkg_metadata
    =============================
    Method to update the metadata file contains information on the packages installed by ggd. This method 
     uses the "get_conda_package_list" method, a method to get the ggd packages from 'conda list', copies 
     the tar.bz2 files to the ggd_info dir, and creates a channeldata.json file using "conda index". The
     channeldata.json metadata file contains information on the installed ggd recipes

    if:
        remove_old == True
        exclude_pkg != None (== some ggd package name)
    then:
        remove package from conda info list (Should be removed, but isn't because conda session still active. Used during uninstall)

    if:
        remove_old == False
        add_package != None (== some ggd package name)
    then:
        do not re build ggd_info. 
        Remove "add_package", a ggd package name, if it exists in the noarch dir
        Add only that package to the dir and re-index ggd_info 
        (Should speed up install)

    Parameters:
    ----------
    1) prefix: The conda environment/prefix to update. (Default = the current conda environment)
    2) channel: The conda channel the packages are from. (Default = ggd-genomics)
    3) remove_old: whether or not to compelete remove the ggd_info dir and re-create it
    4) exclude_pkg: The name of a package to exclude during a rebuild. (The remove_old parameter must be set to True) (Default = None)
    5) add_package: A ggd package name to add to the the ggd info metadata. This should be paired with remove_old = False. Only this package will be added to the metadata.
    """
    


    ## Check that the add_package parameter is paried properly with the remove_old. If incorectly paired, change add_package to avoid removing all metadata except for the single indicated package
    if add_package != None and remove_old == True:
        add_package = None
        print("\n\t-> Warning: You indicated to add a single package to ggd info metadata but also indicated to re-build the metadata. This would result in the single indicated package being the only package in the metadata.")
        print("\n\t    The ggd info metadata will be re-built and all ggd packages will be added.")

    ## Check prefix
    if prefix == None:
        prefix = conda_root()
    else: 
        prefix_in_conda(prefix)

    ## Get the ggd info metadata dir
    ggd_info_dir = os.path.join(prefix,"share","ggd_info")

    ## Remove old ggd_info dir and re-create it
    if remove_old:
        if os.path.isdir(ggd_info_dir):
            shutil.rmtree(ggd_info_dir)

    ## Make metadata dir if it doesn't exist
    if not os.path.isdir(ggd_info_dir):
        os.makedirs(ggd_info_dir)
        os.makedirs(os.path.join(ggd_info_dir,"noarch"))
        with open(os.path.join(ggd_info_dir,"channeldata.json"),"w") as f:
            f.write("{}")

    ## Create the "noarch" dir
    if not os.path.isdir(os.path.join(ggd_info_dir,"noarch")):
        os.makedirs(os.path.join(ggd_info_dir,"noarch"))

    ## Remove a duplicate package being added 
    if add_package != None and remove_old == False: 
        current = [re.search(add_pacakge+".+",x).group() for x in os.listdir(os.path.join(ggd_info_dir,"noarch")) if re.search(add_package,x) != None]
        if current:
            os.remove(os.path.join(ggd_info_dir,"noarch",current[0]))

    ## Get a list of pkgs installed in a conda environemnt (Using conda list)
    pkg_list = get_conda_package_list(prefix,add_package) if add_package != None else get_conda_package_list(prefix)  

    ## Get the dir to the pkgs dir
    pkg_dir = os.path.join(prefix,"pkgs")

    ## Remove package from list if specified and for some reason is in the conda package list 
    if exclude_pkg != None and remove_old == True:
        if exclude_pkg in pkg_list.keys():
            try: 
                assert not os.path.exists(os.path.join(pkg_dir,"{}-{}-{}.tab.bz2".format(exclude_pkg,pkg_list[exclude_pkg]["version"],pkg_list[exclude_pkg]["build"]))), ("\n\t-> ERROR: The package to exclude `{p}` is still installed on your system.".format(p=exclude_pkg))
            except AssertionError as e:
                print(str(e))
                sys.exit(1)
            pkg_list.pop(exclude_pkg)

    ## Copy the ggd package tarfiles to the ggd info dir
    for pkg_name in pkg_list.keys():
        version = pkg_list[pkg_name]["version"]
        build = pkg_list[pkg_name]["build"]
        tarfile_path = os.path.join(pkg_dir,"{}-{}-{}.tar.bz2".format(pkg_name,version,build))
        
        try:
            shutil.copy2(tarfile_path, os.path.join(ggd_info_dir,"noarch"))
        except OSError as e:
            sys.exit(e)

    ## index the .tar.bz2 files in the ggd info metadata dir 
    out = sp.check_call(['conda', 'index', ggd_info_dir, '-n',  channel],stdout=sp.PIPE,stderr=sp.PIPE)

    return(True)


def validate_build(build, species):
    """
    Method to validate that a genome-build is correclty assigned based on a species.
    """
    if build != "*":
        builds_list = get_builds(species)
        if not builds_list or build not in builds_list:
            if species != "*":
                print("Unknown build '%s' for species '%s'" % (build, species), file=sys.stderr)
            else:
                print("Unknown build '%s'" % (build), file=sys.stderr)
            if (builds_list):
                print("Available builds: '%s'" % ("', '".join(builds_list)), file=sys.stderr)
            return False
    return True


def conda_root():
    """ Method used to get the conda root 

    conda_root
    ==========
    This method is used to get the conda root dir. A string representing the conda root dir path 
    is returned.
    """

    croot = check_output(['conda', 'info', '--root'])
    conda_env, conda_path = get_conda_env()
    if conda_env != "base":
        croot = conda_path
    return(croot)


def get_conda_env():
    """Method used to get the current conda environment

    get_conda_env
    =============
    This method is used to get the current conda environment used to access the 
     ggd environment variables created for this specific environment. 

    Returns:
    ++++++++
    1) The conda environment name
    2) The path to the conda environent
    """

    env_info = check_output(["conda", "info", "--envs"])
    fields = env_info.split("\n")
    curr_env = ""
    for field in fields:
        if len(field) > 0 and field[0] != "#":
            env = field.split()
            if len(env) > 0 and "*" in env:
                return env[0],env[-1]
    print("Error in checking conda environment. Verify that conda is working and try again.", file=sys.stderr)
    exit()


def active_conda_env():
    """Method used to get the active conda environmnet

    active_conda_env
    ================
    This method is used to get the active conda environment. A string representing the active environment 
    is retunred. 
    """

    environment_list = sp.check_output(['conda', 'info', '--env']).decode("utf8").strip().split("\n")
    active_environment = "base"
    for environment in environment_list:
        if "*" in environment_list:
            active_environment = env.split(" ")[0]
    return(active_environment)


def prefix_in_conda(prefix):
    """Method to check if a perfix is a conda environment or not

    prefix_in_conda
    ===============
    This method is used to check if a full file path is a conda environment or not. If it is
     True is returned. If it is not, the CondaEnvironmentNotFound error is raised

    Parameters:
    -----------
    1) prefix: The conda enviroment full file path/prefix

    Returns:
    ++++++++
    1) True if prefix is a conda environment, raises an error otherwise
    """

    environments = [os.path.join(x+"/") for x in check_output(["conda", "info", "--env"]).strip().replace("*","").replace("\n"," ").split(" ") if os.path.isdir(x)]
    cbase = min(environments)

    if prefix[-1] != "/":
        prefix = prefix+"/" 
    ## Check that the file path includes the conda base directory
    if cbase not in prefix: 
        raise CondaEnvironmentNotFound(prefix)
    ## Check that the file is in the enviroment lists
    if prefix not in environments:
        raise CondaEnvironmentNotFound(prefix)
    ## Check that the prefix is an existing directory
    if not os.path.isdir(prefix):
        raise CondaEnvironmentNotFound(prefix)
    
    return(True)


class CondaEnvironmentNotFound(Exception):
    """
    Exception Class for a bad conda environment given 
    """
    def __init__(self, location):
        self.message = "The prefix supplied is not a conda enviroment: %s\n" %(location)
        return_code = 1
        sys.tracebacklimit = 0
        print("\n")
        super(CondaEnvironmentNotFound, self).__init__(self.message)

    def __str__(self):
        return(self.message)


def get_conda_package_list(prefix, regex=None):
    """
    This method is used to get the list of packages in a specifc conda environmnet (prefix). Rather then running 
     `conda list` itself, it uses the conda module to grab the information 

    
    Parameters:
    -----------
    1) prefix: The directory path to a conda environment in which you would like to extract the ggd data packages that have been installed
    2) regex: A pattern to match to (default = None)

    Returns:
    +++++++
    1) A dictionary with the package name as a key, and the value as another dictionary with name, version, build, and channel keys
    """
    
    import conda
    from logging import getLogger
    from conda.gateways import logging
    from conda.core.prefix_data import PrefixData
    from conda.base.context import context
    from conda.cli.main_list import get_packages

    ## Get a list of availble ggd channels
    ggd_channels = ["ggd-"+x for x in get_ggd_channels()]
    
    ## Get a prefix data object with installed package information
    installed_packages = sorted(PrefixData(prefix).reload().iter_records(), key=lambda x: x.name)

    ## Create a dictionary with ggd packages
    package_dict = {}
    for precs in get_packages(installed_packages, regex):
        if str(precs.schannel) in ggd_channels: ## Filter based off packages from the ggd channels only
            package_dict[precs.name] = {"name":precs.name,"version":precs.version,"build":precs.build,"channel":precs.schannel}

    return(package_dict)


def bypass_satsolver_on_install(pkg_name, conda_channel="ggd-genomics",debug=False,prefix=None):
    """Method to bypass the sat solver used by conda when a cached recipe is being installed

    bypass_satsolver_on_install
    ============================
    This method is used to run the conda install steps to install a ggd aws cahced reicpe. The
        intsallation will skip the sat solver step, ignore packages that may be additionaly installed
        or uninstalled, and performs other steps in order to install the data package without using 
        the sat solver. 
    The majority of the work is still done by conda through the use of the conda module. This method
        should only be used when a cached recipe is being installed.

    Parameters:
    -----------
    1) pkg_name: The name of the ggd package to install. (Example: hg19-gaps)
    2) conda_channel: The ggd conda channel that package is being installed from. (Example: ggd-genomics)
    """

    #-------------------------------------------------------------------------
    # import statments 
    #-------------------------------------------------------------------------
    from conda.base.context import context 
    from conda.cli import common
    from conda.cli import install
    from conda.core.solve import Solver
    from conda.core.solve import SolverStateContainer
    from conda.common.io import Spinner
    from conda.core.link import PrefixSetup
    from conda.core.link import UnlinkLinkTransaction
    from argparse import Namespace
    from conda._vendor.boltons.setutils import IndexedSet
    from conda.models.prefix_graph import PrefixGraph
    from conda.core.solve import diff_for_unlink_link_precs
    from conda.common.compat import iteritems, itervalues, odict, text_type
    from conda._vendor.toolz import concat, concatv
    from conda.resolve import Resolve
    from conda.models.match_spec import MatchSpec
    from conda.base.constants import UpdateModifier
    from conda.common.io import ProgressBar
    from conda.gateways.logging import set_all_logger_level, set_conda_log_level
    from conda.gateways.logging import VERBOSITY_LEVELS
    from conda.gateways.logging import log
    from logging import DEBUG, ERROR, Filter, Formatter, INFO, StreamHandler, WARN, getLogger
    import sys 

    print("\n\t-> Installing %s from the %s conda channel\n" %(pkg_name, conda_channel))

    #-------------------------------------------------------------------------
    # Nested functions 
    #-------------------------------------------------------------------------
    def bypass_sat(package_name,ssc_object): ## Package_name will be used as a key
        """Method used to extract information during sat solving, but to bypass the sat solving step

        bypass_sat
        ==========
        This method is used to extract and process information that would have been done during the sat
        solvering step, (Solving Enviroment), bypass the sat solver, and return a filtered set of packages
        to install.

        Parameters:
        -----------
        1) package_name: The name of the package to extract. (This is the package that will be installed)
        2) ssc_object: A processed conda SolverStateContainer object. 

        Returns:
        +++++++
        1) The updated ssc object based off the sat bypass and package filtering. 

        """
        
        ## From Solver.run_sat
        specs_map_set = set(itervalues(ssc_object.specs_map))

        ## Get the specs from ssc filtered by the package name
        final_environment_specs = IndexedSet(concatv(itervalues(odict([(package_name,ssc_object.specs_map[package_name])])), ssc_object.track_features_specs, ssc_object.pinned_specs))

        ## Run the resolve process and get info for desired package
        ssc_object.solution_precs = ssc_object.r.solve(tuple(final_environment_specs))

        ## Filter ssc.solution_precs
        wanted_indices = []
        for i, info in enumerate(ssc_object.solution_precs):
            if package_name in ssc_object.solution_precs[i].namekey:
                wanted_indices.append(i)

        filtered_ssc_solution_precs = [ssc_object.solution_precs[x] for x in wanted_indices]
        ssc_object.solution_precs = filtered_ssc_solution_precs

        ## Add the final environment specs to ssc
        ssc_object.final_environment_specs = final_environment_specs

        return(ssc_object)


    #-------------------------------------------------------------------------
    # Run install 
    #-------------------------------------------------------------------------

    ## Set the context.always_yes to True to bypass user input
    context.always_yes = True

    target_prefix = context.target_prefix
    if prefix != None:
        target_prefix = prefix

    # Setup solver object
    solve = Solver(target_prefix, (conda_channel,u'default'), context.subdirs, [pkg_name])

    ## Create a solver state container 
    ### Make sure to Freeze those packages already installed in the current env in order to bypass update checking.  
    ssc = SolverStateContainer(prefix=context.target_prefix, update_modifier=UpdateModifier.FREEZE_INSTALLED, 
                               deps_modifier=context.deps_modifier, prune=True, ignore_pinned=context.ignore_pinned, 
                               force_remove=context.force_remove, should_retry_solve=False)

    ## Get channel metadata
    with Spinner("Collecting package metadata", not context.verbosity and not context.quiet, context.json):
        ssc = solve._collect_all_metadata(ssc)

    ## Set specs map to an empty map. (No need to check other specs)
    add_spec = []
    for p_name, spec  in iteritems(ssc.specs_map):
        if str(p_name) == pkg_name:
            add_spec.append((pkg_name, MatchSpec(pkg_name)))

    ssc.specs_map = odict(add_spec)

    ## Process the data in the solver state container 
    with Spinner("Processing data", not context.verbosity and not context.quiet, context.json):
        ssc = solve._add_specs(ssc)
        ssc = bypass_sat(pkg_name, ssc)
        ssc = solve._post_sat_handling(ssc)

    ## create an IndexedSet from ssc.solution_precs
    ssc.solution_precs = IndexedSet(PrefixGraph(ssc.solution_precs).graph)

    ## Get linked and unlinked 
    unlink_precs, link_precs = diff_for_unlink_link_precs(target_prefix, ssc.solution_precs, solve.specs_to_add)

    #set unlinked to empty indexed set so we do not unlink/remove any pacakges 
    unlink_precs = IndexedSet()

    ## Create a PrefixSetup
    stp = PrefixSetup(solve.prefix, unlink_precs, link_precs, solve.specs_to_remove, solve.specs_to_add)

    ## Create an UnlinkLinkTransaction with stp
    unlink_link_transaction = UnlinkLinkTransaction(stp)

    #create Namespace
    args = Namespace(channel=None, cmd="install", deps_modifier=context.deps_modifier, json=False, packages=[pkg_name])

    ## Set logger level
    if debug:
        WARN, INFO, DEBUG, TRACE = VERBOSITY_LEVELS
        set_all_logger_level(DEBUG)

    ## Install package
    install.handle_txn(unlink_link_transaction, solve.prefix, args, False)
    
    ## Retrun True if finished
    return(True)
        

if __name__ == "__main__":
    import doctest
    doctest.testmod()



