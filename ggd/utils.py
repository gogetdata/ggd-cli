from __future__ import print_function
import os
import sys
import glob
from git import Repo
import subprocess as sp
import requests
import locale

LOCAL_REPO_DIR = os.getenv("GGD_LOCAL", os.path.expanduser("~/.config/"))
RECIPE_REPO_DIR = os.path.join(LOCAL_REPO_DIR, "ggd-recipes")
GITHUB_URL = "https://github.com/gogetdata/ggd-recipes.git"
METADATA_REPO_DIR = os.path.join(LOCAL_REPO_DIR, "ggd-metadata")
METADATA_GITHUB_URL = "https://github.com/gogetdata/ggd-metadata"
GGD_CLI_REQUIREMENTS = "https://raw.githubusercontent.com/gogetdata/ggd-cli/master/requirements.txt"


def get_species(update_repo=True):
    """ Method to get available annotated species in the ggd repo

    get_species
    ===========
    This method is used to get a list of all available/annotated species in the 
    ggd repo. It returns a list of species
    """

    if update_repo:
        update_local_repo()
    elif not os.path.isdir(LOCAL_REPO_DIR): ## If There is no local repo directory 
        update_local_repo()

    genomes_dir = os.path.join(RECIPE_REPO_DIR, "genomes")
    return os.listdir(genomes_dir)


def get_ggd_channels():
    """Method used to get avaiable ggd channels
    
    get_ggd_channels
    ================
    This method is used to get all avaiable/created ggd conaa channels.
    This method will return a list of ggd conda channels.
    """

    recipe_dir = os.path.join(RECIPE_REPO_DIR, "recipes")
    return os.listdir(recipe_dir)


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

    update_metadata_local_repo()
    channeldata_path = os.path.join(METADATA_REPO_DIR, "channeldata", ggd_channel, "channeldata.json")
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
    update_local_repo()
    species_dir = os.path.join(RECIPE_REPO_DIR, "genomes", species)

    if species == "*":
        paths = glob.glob(species_dir)
        builds = []
        for path in paths:
            builds.extend(os.listdir(path))
        return builds
    else:
        if os.path.isdir(species_dir):
            return os.listdir(species_dir)


def update_metadata_local_repo():
    """Method to update the ggd-metadata local repo

    update_metadata_local_repo()
    ============================
    This method is used to update the ggd-metadata local repo. This local repo is used
     to get information about the metadata for ggd recipes. This method updates the local
     repo with any changes that have occured since the last update.
    """

    if not os.path.isdir(LOCAL_REPO_DIR):
        os.makedirs(LOCAL_REPO_DIR)
    if not os.path.isdir(METADATA_REPO_DIR):
        Repo.clone_from(METADAT_GITHUB_URL, METADATA_REPO_DIR)
    Repo(METADATA_REPO_DIR).remotes.origin.pull()


def update_local_repo():
    """Method to update the local ggd-recipes repo
    
    update_local_repo
    =================
    This method is used to update the a local version of the ggd-recipe repo. This local 
     ggd-recipe repo is used to access information about the repo. This method updates the 
     local repo with any changes made to the repo since the last update. 
    """

    if not os.path.isdir(LOCAL_REPO_DIR):
        os.makedirs(LOCAL_REPO_DIR)
    if not os.path.isdir(RECIPE_REPO_DIR):
        Repo.clone_from(GITHUB_URL, RECIPE_REPO_DIR)
    Repo(RECIPE_REPO_DIR).remotes.origin.pull()


def validate_build(build, species):
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

    environment_list = sp.check_output(['conda', 'info', '--env']).strip().split("\n")
    active_environment = "base"
    for environment in environment_list:
        if "*" in environment_list:
            active_environment = env.split(" ")[0]
    return(active_environment)


def bypass_satsolver_on_install(pkg_name, conda_channel="ggd-genomics"):
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

    # Setup solver object
    solve = Solver(context.target_prefix, (conda_channel,u'default'), context.subdirs, [pkg_name])

    ## Create a solver state container 
    ssc = SolverStateContainer(context.target_prefix, context.update_modifier, context.deps_modifier, context.prune, context.ignore_pinned, context.force_remove)

    ## Get channel metadata
    with Spinner("Collecting package metadata", not context.verbosity and not context.quiet, context.json):
        ssc = solve._collect_all_metadata(ssc)

    ## Process the data in the solver state container 
    with Spinner("Processing data", not context.verbosity and not context.quiet, context.json):
        ssc = solve._add_specs(ssc)
        ssc = bypass_sat(pkg_name, ssc)
        ssc = solve._post_sat_handling(ssc)
        ssc = solve._check_solution(ssc)

    ## create an IndexedSet from ssc.solution_precs
    ssc.solution_precs = IndexedSet(PrefixGraph(ssc.solution_precs).graph)

    ## Get linked and unlinked 
    unlink_precs, link_precs = diff_for_unlink_link_precs(context.target_prefix, ssc.solution_precs, solve.specs_to_add)

    #set unlinked to empty indexed set so we do not unlink/remove any pacakges 
    unlink_precs = IndexedSet()

    ## Create a PrefixSetup
    stp = PrefixSetup(solve.prefix, unlink_precs, link_precs, solve.specs_to_remove, solve.specs_to_add)

    ## Create an UnlinkLinkTransaction with stp
    unlink_link_transaction = UnlinkLinkTransaction(stp)

    #create Namespace
    args = Namespace(channel=None, cmd="install", deps_modifier=context.deps_modifier, json=False, packages=[pkg_name])

    ## Set logger level
    #WARN, INFO, DEBUG, TRACE = VERBOSITY_LEVELS
    #set_all_logger_level(DEBUG)

    ## Install package
    install.handle_txn(unlink_link_transaction, solve.prefix, args, False)
        

if __name__ == "__main__":
    import doctest
    doctest.testmod()



