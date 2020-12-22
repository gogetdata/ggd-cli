from __future__ import print_function

import json
import locale
import os
import re
import shutil
import subprocess as sp
import sys

import requests

# ---------------------------------------------------------------------------------------------------------------------------------
## Global Variables
# ---------------------------------------------------------------------------------------------------------------------------------

## GGD variables
LOCAL_REPO_DIR = os.getenv("GGD_LOCAL", os.path.expanduser("~/.config/ggd-info/"))
GENOME_METADATA_DIR = os.path.join(LOCAL_REPO_DIR, "genome_metadata")
CHANNEL_DATA_DIR = os.path.join(LOCAL_REPO_DIR, "channeldata")
RECIPE_REPO_DIR = os.path.join(LOCAL_REPO_DIR, "ggd-recipes")
GGD_CLI_REQUIREMENTS = (
    "https://raw.githubusercontent.com/gogetdata/ggd-cli/master/requirements.txt"
)


## Repodata variables
REPODATA_URL = "https://conda.anaconda.org/{channel}/{subdir}/repodata.json"
REPODATA_LABELED_URL = "https://conda.anaconda.org/{channel}/label/{label}/{subdir}/repodata.json"
REPODATA_DEFAULTS_URL = "https://repo.anaconda.com/pkgs/main/{subdir}/repodata.json"


## GGD META RECIPE URL
GGD_META_RECIPE_URL = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/meta-recipes/{meta_recipe_name}/{file_name}"

## META RECIPE JSON OUTPUT FILE
GGD_META_RECIPE_ENV_JSON = "GGD_METARECIPE_ENVIRONMENT_VARIABLES.json"
GGD_META_RECIPE_FINAL_COMMANDS = "GGD_METARECIPE_FINAL_COMMANDS.sh"


# ---------------------------------------------------------------------------------------------------------------------------------
## Functions/methods
# ---------------------------------------------------------------------------------------------------------------------------------

def get_species(update_files=True, full_dict=False):
    """ Method to get available annotated species in the ggd repo

    get_species
    ===========
    This method is used to get a list of all available/annotated species in the 
    ggd repo. It returns a list of species

    Parameters:
    ----------
    1) update_files: (bool) Default=True. Update the local files before getting species
    2) full_dict:    (bool) Default=False. Get the full dictionary with keys as species and values as genome builds

    Returns:
    ++++++++
    1) (list) If full_dict = False, a list of species
    or
    2) (dict) If full_dict = True, a dictionary with species as key and available genome builds as values 
    """

    if update_files and check_for_internet_connection():
        update_genome_metadata_files()

    if full_dict:
        with open(os.path.join(GENOME_METADATA_DIR, "species_to_build.json"), "r") as f:
            return json.load(f)
    else:
        with open(os.path.join(GENOME_METADATA_DIR, "species_to_build.json"), "r") as f:
            return json.load(f).keys()


def get_ggd_channels():
    """Method used to get available ggd channels
    
    get_ggd_channels
    ================
    This method is used to get all available/created ggd conaa channels.
    This method will return a list of ggd conda channels.

    Run get_species() before running get_ggd_channels(). get_species triggers an update
     of local genomic metadata files
    """

    with open(os.path.join(GENOME_METADATA_DIR, "ggd_channels.json"), "r") as f:
        return json.load(f)["channels"]


def get_channel_data(ggd_channel):
    """Method used to get locally stored channel meta data for a specific ggd channel

    get_channel_data
    ================
    This method is used to get the ggd local channel's metadata json file. 

    Parameters:
    -----------
    1) ggd_channel: (str) The ggd channel to get metadata for

    Returns:
    +++++++
    1) (str) The file path to the metadata file for the specific channel
    """

    if check_for_internet_connection():
        update_channel_data_files(ggd_channel)

    channeldata_path = os.path.join(CHANNEL_DATA_DIR, ggd_channel, "channeldata.json")
    return channeldata_path


def get_channeldata_url(ggd_channel):
    """Method used to get a url for the metadata json file for a specific ggd channel
    
    get_channeldata_url
    ===================
    This method is used to get a url for a specific metadata json file for a specific ggd conda channel

    Parameters:
    -----------
    1) ggd_channel: (str) The ggd channel to get the metadata json file url for 

    Returns:
    ++++++++
    1) (str) The url for the metadata file
    """

    ## Update local channel data file if internet connection available
    if check_for_internet_connection():
        update_channel_data_files(ggd_channel)

    return os.path.join(
        "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/channeldata",
        ggd_channel,
        "channeldata.json",
    )


def get_required_conda_version():
    """Method to get the conda version from the ggd-cli requirements file

    get_required_conda_version
    ==========================
    This method is used to get the required version for conda based on the version set in the 
     requirements file in ggd-cli. This version can be used to maintain the correct version while 
     using ggd

    Return:
    +++++++
    1) (str) The required version if found, else -1
    2) (str) An = or >= depending on the requirement
    """

    req = requests.get(GGD_CLI_REQUIREMENTS, stream=True)

    conda_version = -1
    equals = "="
    for line in req.iter_lines():
        if "conda=" in str(line.decode()):
            conda_version = str(line.decode()).strip().split("=")[1]
        elif "conda>=" in str(line.decode()):
            conda_version = str(line.decode()).strip().split(">=")[1]
            equals = ">="
    return conda_version, equals


def check_output(args, **kwargs):
    """Method to get a byte converted string from a subprocess command """

    return _to_str(sp.check_output(args, **kwargs).strip())


def _to_str(s, enc=locale.getpreferredencoding()):
    """Method to convert a bytes into a string based on a local preferred encoding  

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
        with open(os.path.join(GENOME_METADATA_DIR, "build_to_species.json"), "r") as f:
            return json.load(f).keys()
    else:
        ## Check if species is real
        with open(os.path.join(GENOME_METADATA_DIR, "species_to_build.json"), "r") as f:
            jdict = json.load(f)
            if species not in jdict.keys():
                sys.exit(
                    "'{s}' is not an available species in ggd. Please contact the ggd team to have it added".format(
                        s=species
                    )
                )
            else:
                return jdict[species]


def check_for_internet_connection(t=5):
    """
    Method to check if there is an internet connection or not
    """

    from pytest_socket import SocketBlockedError

    url = "http://www.google.com/"
    timeout = t
    try:
        _ = requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        pass
    except SocketBlockedError:
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
    1) channel: (str) The channel to download for the channeldata
    """

    if channel in get_ggd_channels():

        if not os.path.isdir(LOCAL_REPO_DIR):
            os.makedirs(LOCAL_REPO_DIR, mode=0o777)
        if not os.path.isdir(CHANNEL_DATA_DIR):
            os.makedirs(CHANNEL_DATA_DIR, mode=0o777)

        channel_dir = os.path.join(CHANNEL_DATA_DIR, channel)
        if not os.path.isdir(channel_dir):
            os.makedirs(channel_dir, mode=0o777)

        ## Dowload json file
        channeldata_url = os.path.join(
            "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/channeldata/",
            channel,
            "channeldata.json",
        )

        channeldata_json = requests.get(channeldata_url).json()
        with open(os.path.join(channel_dir, "channeldata.json"), "w") as c:
            json.dump(channeldata_json, c)

    else:
        sys.exit("The '{c}' channel is not a ggd conda channel".format(c=channel))

    return True


def update_genome_metadata_files():
    """Method to update the species and genome build, and ggd channel metadata files locally 

    update_genome_metadata_files
    ==========================================
    This method will download the json metadata species and genome-build files from ggd-metadata and store 
     in the LOCAL_REPO_DIR. 
    """

    if not os.path.isdir(LOCAL_REPO_DIR):
        os.makedirs(LOCAL_REPO_DIR, mode=0o777)
    if not os.path.isdir(GENOME_METADATA_DIR):
        os.makedirs(GENOME_METADATA_DIR, mode=0o777)

    ## Download the json files
    build_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/genome_metadata/build_to_species.json"
    species_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/genome_metadata/species_to_build.json"
    ggd_channels_url = "https://raw.githubusercontent.com/gogetdata/ggd-metadata/master/genome_metadata/ggd_channels.json"

    buildjson = requests.get(build_url).json()
    with open(os.path.join(GENOME_METADATA_DIR, "build_to_species.json"), "w") as b:
        json.dump(buildjson, b)

    speciesjson = requests.get(species_url).json()
    with open(os.path.join(GENOME_METADATA_DIR, "species_to_build.json"), "w") as s:
        json.dump(speciesjson, s)

    channeljson = requests.get(ggd_channels_url).json()
    with open(os.path.join(GENOME_METADATA_DIR, "ggd_channels.json"), "w") as s:
        json.dump(channeljson, s)

    return True


def get_run_deps_from_tar(tarfile_path, channel):
    """Get a list of ggd packages that are run dependencies of another ggd packages

    get_run_deps_from_tar
    =====================
    Method to extract all ggd specific run dependencies of another ggd package.

    Parameters:
    ----------
    1) tarfile_path: (str) Path to the package tarfile to search for deps in 
    2) channel:      (str) The ggd chanenl the tarball file package is for

    Returns:
    +++++++
    1) (list) A list of all ggd specific package deps
    """

    import json
    import tarfile

    import requests
    import yaml

    ## extract channel
    channel = channel.strip().split("-")[-1]

    ## If internet connection
    if check_for_internet_connection(3):
        ggd_package_dict = requests.get(get_channeldata_url(channel)).json()
    else:
        with open(get_channel_data(channel)) as json_file:
            ggd_package_dict = json.load(json_file)

    ## Get a list of all ggd packages
    ggd_package_names = set(ggd_package_dict["packages"].keys())

    ## Check for ggd packages in run requirements
    with tarfile.open(tarfile_path, "r:bz2") as tarball_file:
        meta_yaml = yaml.safe_load(
            tarball_file.extractfile(
                tarball_file.getmember("info/recipe/meta.yaml.template")
            )
        )

        ## Add any ggd packages that are requirements to the req package list
        req_packages = [
            req for req in meta_yaml["requirements"]["run"] if req in ggd_package_names
        ]

    return req_packages


def update_installed_pkg_metadata(
    prefix=None,
    channel="ggd-genomics",
    remove_old=True,
    exclude_pkg=None,
    add_packages=[],
    include_local=True,
):
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
    1) prefix:        (str)  The conda environment/prefix to update. (Default = the current conda environment)
    2) channel:       (str)  The conda channel the packages are from. (Default = ggd-genomics)
    3) remove_old:    (bool) whether or not to complete remove the ggd_info dir and re-create it
    4) exclude_pkg:   (str)  The name of a package to exclude during a rebuild. (The remove_old parameter must be set to True) (Default = None)
    5) add_package:   (str)  A ggd package name to add to the the ggd info metadata. This should be paired with remove_old = False. Only this package will be added to the metadata.
    7) include_local: (bool) Whether or not to include package installed locally. (Default = True)
    """

    ## Check that the add_package parameter is paired properly with the remove_old. If incorrectly paired, change add_package to avoid removing all metadata except for the single indicated package
    if add_packages and remove_old == True:
        add_packages = None
        print(
            "\n:ggd:update-metadata: Warning: You indicated to add a single package to ggd info metadata but also indicated to re-build the metadata. This would result in the single indicated package being the only package in the metadata."
        )
        print(
            "\n:ggd:update-metadata:\t The ggd info metadata will be re-built and all ggd packages will be added."
        )

    ## Check prefix
    if prefix == None:
        prefix = conda_root()
    else:
        prefix_in_conda(prefix)

    ## Get the ggd info metadata dir
    ggd_info_dir = os.path.join(prefix, "share", "ggd_info")

    ## Check the conda pkg dir for deviation in the installed tar files
    if os.path.isdir(ggd_info_dir):
        check_conda_pkg_dir(prefix, exclude_pkg)

    ## Remove old ggd_info dir and re-create it
    if remove_old:
        if os.path.isdir(ggd_info_dir):
            shutil.rmtree(ggd_info_dir)

    ## Make metadata dir if it doesn't exist
    if not os.path.isdir(ggd_info_dir):
        os.makedirs(ggd_info_dir, mode=0o777)
        os.makedirs(os.path.join(ggd_info_dir, "noarch"), mode=0o777)
        with open(os.path.join(ggd_info_dir, "channeldata.json"), "w") as f:
            f.write("{}")

    ## Create the "noarch" dir
    if not os.path.isdir(os.path.join(ggd_info_dir, "noarch")):
        os.makedirs(os.path.join(ggd_info_dir, "noarch"), mode=0o777)

    ## Check add packages
    if add_packages and remove_old == False:
        for (
            add_package
        ) in (
            add_packages
        ):  ## Iterate over each of the installed data packages and check for duplicates
            current = [
                re.search(add_package + ".+", x).group()
                for x in os.listdir(os.path.join(ggd_info_dir, "noarch"))
                if re.search(add_package, x) != None
            ]
            if current:
                os.remove(os.path.join(ggd_info_dir, "noarch", current[0]))

    ## Get the dir to the pkgs dir
    pkg_dir = os.path.join(prefix, "pkgs")

    ## Get a list of pkgs installed in a conda environemnt (Using conda list)
    pkg_list = {}
    if add_packages:
        for add_package in add_packages:

            ## Add package to package list
            pkg_dict = get_conda_package_list(
                prefix, add_package, include_local=include_local
            )
            pkg_list.update(pkg_dict)

            ## Check for any ggd specific run deps and add them to the package list
            tarfile = os.path.join(
                pkg_dir,
                "{}-{}-{}.tar.bz2".format(
                    add_package,
                    pkg_dict[add_package]["version"],
                    pkg_dict[add_package]["build"],
                ),
            )
            for pkg in get_run_deps_from_tar(tarfile, channel):
                pkg_list.update(
                    get_conda_package_list(prefix, pkg, include_local=include_local)
                )

    else:
        pkg_list.update(get_conda_package_list(prefix, include_local=include_local))

    ## Remove package from list if specified and for some reason is in the conda package list
    if exclude_pkg != None and remove_old == True:
        if exclude_pkg in pkg_list.keys():
            try:
                assert not os.path.exists(
                    os.path.join(
                        pkg_dir,
                        "{}-{}-{}.tab.bz2".format(
                            exclude_pkg,
                            pkg_list[exclude_pkg]["version"],
                            pkg_list[exclude_pkg]["build"],
                        ),
                    )
                ), "\n\t-> ERROR: The package to exclude `{p}` is still installed on your system.".format(
                    p=exclude_pkg
                )
            except AssertionError as e:
                print(str(e))
                sys.exit(1)
            pkg_list.pop(exclude_pkg)

    ## Copy the ggd package tarfiles to the ggd info dir
    for pkg_name in pkg_list.keys():
        version = pkg_list[pkg_name]["version"]
        build = pkg_list[pkg_name]["build"]
        tarfile_path = os.path.join(
            pkg_dir, "{}-{}-{}.tar.bz2".format(pkg_name, version, build)
        )

        try:
            shutil.copy2(tarfile_path, os.path.join(ggd_info_dir, "noarch"))
        except OSError as e:
            sys.exit(e)

    ## index the .tar.bz2 files in the ggd info metadata dir
    out = sp.check_call(
        ["conda", "index", ggd_info_dir, "-n", channel], stdout=sp.PIPE, stderr=sp.PIPE
    )

    return True


def check_conda_pkg_dir(prefix, exclude_pkg=None):
    """Method to check that the conda pkg directory contains the tar files in the ggd list directory

    check_conda_pkg_dir
    ===================
    Method to check that the conda pkg directory contains the tar files for installed ggd recipes. This is 
     useful if for some reason the .tar.bz2 files are removed from the conda pkg dir. This is seen to happen 
     if someone runs `conda clean`. This will make sure that ggd tar files are maintined. 

    Parameters:
    ----------
    1) prefix:      (str) The conda environment/prefix to update. (Default = the current conda environment)
    2) exclude_pkg: (str) The name of a package to exclude during a rebuild. (The remove_old parameter must be set to True) (Default = None)
    
    Returns:
    ++++++++
    (bool) True if no errors, False if copy error
    """

    ## Get the ggd info metadata dir
    ggd_info_dir = os.path.join(prefix, "share", "ggd_info")

    ## Get the dir to the pkgs dir
    pkg_dir = os.path.join(prefix, "pkgs")
    conda_pkg_files = set(os.listdir(pkg_dir))

    ## Conda list for ggd recipes. IF exclude_pkg is set, the key will be removed from this set
    installed_pkgs = set(
        [
            key + "-" + value["version"] + "-" + value["build"] + ".tar.bz2"
            for key, value in get_conda_package_list(prefix).items()
            if key != exclude_pkg
        ]
    )

    ## Check if the .tar.bz2 files are in the conda pkg dir or not, and fix if not
    for f in os.listdir(os.path.join(ggd_info_dir, "noarch")):

        ## Only look at .tar.bz2 files
        if not f.endswith(".tar.bz2"):
            continue

        ## IF file is installed but not present in the conda_pkg_files, copy it to the conda_pkg_files
        if f in installed_pkgs and f not in conda_pkg_files:
            print("ggd:utils: Fixing the {t} file in the conda pkg dir\n".format(t=f))
            try:
                shutil.copy2(os.path.join(ggd_info_dir, "noarch", f), pkg_dir)
            except OSError as e:
                return False

    return True


def validate_build(build, species):
    """
    Method to validate that a genome-build is correctly assigned based on a species.
    """
    if build != "*":
        builds_list = get_builds(species)
        if not builds_list or build not in builds_list:
            if species != "*":
                print(
                    ":ggd:validate-build: Unknown build '%s' for species '%s'"
                    % (build, species),
                    file=sys.stderr,
                )
            else:
                print(
                    ":ggd:validate-build: Unknown build '%s'" % (build), file=sys.stderr
                )
            if builds_list:
                print(
                    ":ggd:validate-build: Available builds: '%s'"
                    % ("', '".join(builds_list)),
                    file=sys.stderr,
                )
            return False
    return True


def conda_root():
    """ Method used to get the conda root 

    conda_root
    ==========
    This method is used to get the conda root dir. A string representing the conda root dir path 
    is returned.
    """

    from conda.base.context import context

    croot = context.root_prefix
    return croot


def get_conda_env(prefix=conda_root()):
    """Method used to get the current conda environment

    get_conda_env
    =============
    This method is used to get the the name and prefix path for a specified conda environment. 
     Used to access ggd environment variables created for this specific environment. 

    Returns:
    ++++++++
    1) (str) The conda environment name
    2) (str) The path to the conda environment
    """

    ## Get environment list
    from conda.core.envs_manager import list_all_known_prefixes

    prefix = prefix.rstrip("/")

    env_var_paths = dict()  ## Key = env_path, value = env_name
    for env_path in list_all_known_prefixes():
        name = os.path.basename(env_path.rstrip("/"))
        env_var_paths[env_path.rstrip("/")] = name

    prefix_path = get_conda_prefix_path(prefix)
    return (env_var_paths[prefix_path], prefix_path)

    print(
        ":ggd:conda-env: Error in checking conda environment. Verify that conda is working and try again.",
        file=sys.stderr,
    )
    sys.exit(1)


def get_conda_prefix_path(prefix):
    """Method to get the conda environment/prefix path from either the actual path or name

    get_conda_prefix_path
    =====================
    This method is used to get the acutal prefix path from a file path or conda environment name 

    Parameters:
    -----------
    1) prefix: (str) The file path or conda environment name to get the prefix path for

    Returns: 
    ++++++++
    1) (str) The prefix path
    
    """

    ## Get environment list
    from conda.core.envs_manager import list_all_known_prefixes

    env_var_names = dict()  ## Key = env_name, value = env_path
    env_var_paths = dict()  ## Key - env_path, value = env_name
    for env_path in list_all_known_prefixes():
        name = os.path.basename(env_path.rstrip("/"))
        env_var_names[name] = env_path.rstrip("/")
        env_var_paths[env_path.rstrip("/")] = name

    prefix = prefix.rstrip("/")

    ## Check that the file is in the environment lists
    if prefix not in env_var_names.keys() and prefix not in env_var_paths.keys():
        raise CondaEnvironmentNotFound(prefix)

    ## Check that the prefix is an existing directory
    prefix_path = prefix
    if prefix in env_var_names.keys():
        prefix_path = env_var_names[prefix]

    return prefix_path


def get_base_env(cur_prefix):
    """
    get_base_env
    ============
    Method to get the base conda environment based on a 
     given prefix, which may or may not be base. 

    Parameters:
    -----------
    1) cur_prefix: (str) The path to the current prefix
    
    Returns:
    ++++++++
    1) (str) The path of the base prefix

    """
    
    ## Get environment list
    from conda.core.envs_manager import list_all_known_prefixes

    ## Get the full path of the conda prefix
    cur_prefix = get_conda_prefix_path(cur_prefix)

    return(min([x for x in list_all_known_prefixes() if x in cur_prefix]))


def prefix_in_conda(prefix):
    """Method to check if a prefix is a conda environment or not

    prefix_in_conda
    ===============
    This method is used to check if a full file path is a conda environment or not. If it is
     True is returned. If it is not, the CondaEnvironmentNotFound error is raised

    Parameters:
    -----------
    1) prefix: (str) The conda environment full file path/prefix

    Returns:
    ++++++++
    1) (bool) True if prefix is a conda environment, raises an error otherwise
    """

    ## Get environment list
    from conda.core.envs_manager import list_all_known_prefixes

    env_var_names = dict()  ## Key = env_name, value = env_path
    env_var_paths = dict()  ## Key - env_path, value = env_name
    for env_path in list_all_known_prefixes():
        name = os.path.basename(env_path.rstrip("/"))
        env_var_names[name] = env_path.rstrip("/")
        env_var_paths[env_path.rstrip("/")] = name

    prefix = prefix.rstrip("/")

    ## Check that the file is in the environment lists
    if prefix not in env_var_names.keys() and prefix not in env_var_paths.keys():
        raise CondaEnvironmentNotFound(prefix)

    ## Get the prefix path dd
    prefix_path = get_conda_prefix_path(prefix)

    ## Get the base/first conda environment for all environments that are subdirs of the specified prefix
    cbase = min([x for x in env_var_paths.keys() if x in prefix_path])

    ## Check that the file path includes the conda base directory
    if cbase not in prefix_path:
        raise CondaEnvironmentNotFound(prefix)

    ## Check that the prefix is an existing directory
    if not os.path.isdir(prefix_path):
        raise CondaEnvironmentNotFound(prefix)

    return True


class CondaEnvironmentNotFound(Exception):
    """
    Exception Class for a bad conda environment given 
    """

    def __init__(self, location):
        self.message = "The prefix supplied is not a conda environment: %s\n" % (
            location
        )
        sys.tracebacklimit = 0
        print("\n")
        super(CondaEnvironmentNotFound, self).__init__(self.message)

    def __str__(self):
        return self.message


class ChecksumError(Exception):
    """
    Exception Class for failed checksum
    """

    def __init__(self, pkg_name):
        self.message = (
            "Data file content validation failed. The %s data package did not install correctly.\n"
            % (pkg_name)
        )
        sys.tracebacklimit = 0
        print("\n")
        super(ChecksumError, self).__init__(self.message)

    def __str__(self):
        return self.message


class literal_block(str):
    pass


def add_yaml_literal_block(yaml_object):
    """
    Get a yaml literal block representer function to convert normal strings into yaml literals during yaml dumping

    Convert string to yaml literal block
    yaml docs: see "Block mappings" in https://pyyaml.org/wiki/PyYAMLDocumentation
    """

    def literal_str_representer(dumper, data):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")

    return yaml_object.add_representer(literal_block, literal_str_representer)


def get_repodata(channels = ["ggd-genomics"], subdirs = ["noarch"], return_repodata = True):
    """
    get_repodata
    ============
    Method to get the conda repodata from the Anaconda Cloud for a list of conda channels 

    Parameters:
    -----------
    1) channels:        (list) A list of channels to check and get repodata for 
    2) subdires:        (list) A list of subdirs (platforms) to check. ("noarch", "linux-64", etc.)
                                Default = ["noarch"]
    3) return_repodata: (bool) True or False, whether or not to return the repodata. If True, the repodata
                                dict and the name 2 tar dict will be returned. If False, only the name 2 tar
                                dict will be returned. (Default = True)

    Returns:
    ++++++++
    if return_repodata is True:
        1) (dict)  A dictionary with keys as channels and values as the repodata for that channel starting at the "packages" key.
        2) (dict)  A dict with keys as channel, subdir, package names and values as a set of tar files.
    if return_repodata is False:
        1) (dict)  A dict with keys as channel, subdir, package names and values as a set of tar files.
    """ 
    from collections import defaultdict

    print("\n:ggd:repodata: Loading repodata from the Anaconda Cloud for the following channels: {}".format(", ".join(channels)))

    ## Load the repodata for each channel
    repodata_by_channel = dict()

    name2tar = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    
    ## Check each channel
    for channel in channels:

        ## No repodata for default (local) channel
        if channel == "defaults":
            continue

        ## Check each platform
        for subdir in subdirs:
            repodata_url = REPODATA_URL.format(channel=channel, subdir=subdir)

            try:
                repodata_json = requests.get(repodata_url).json()
            except ValueError as e:
                print("\n:ggd:repodata: !!ERROR!! A problem occured loading the repodata for the conda channel: '{}' platform: '{}'".format(channel, subdir))
                print(str(e))
                sys.exit(1)

            ## Add to dict
            repodata_by_channel[channel] = repodata_json["packages"]

            ##Create the name2tar file 
            for tar, pkg in repodata_json["packages"].items():
                name = pkg["name"]

                name2tar[channel][subdir][name].add(tar)

    if return_repodata:
        return (repodata_by_channel, name2tar) 
    else:
        return (name2tar) 


def check_for_meta_recipes(name, jdict):
    """
    check_for_meta_recipes
    ======================
    Check whether or not a recipe is a meta-recipe  

    Parameters:
    -----------
    1) name:  (str)  The name of a package
    2) jdict: (dict) A dictionary of packages to check 

    Returns:
    ++++++++
    (bool) True if meta-recipe, false otherwise
    """
    try:
    
        if (jdict["packages"][name]["identifiers"]["genome-build"] == "meta-recipe" 
                and 
            jdict["packages"][name]["identifiers"]["species"] == "meta-recipe"):
            return(True)
        else:
            return(False)
    
    except KeyError as e:
        return(False)


def get_meta_recipe_pkg(pkg_name, jdict, ggd_channel, prefix):
    """
    get_meta_recipe_pkg
    ===================
    Method to download a meta recipe package (.tar.bz2 file) from the Anaconda cloud into the pkgs dir of a
     conda environment (prefix). The repodata is checked for the pkg name in a specific ggd channel. 
     The correct tar file is found and checked. The tar file is then downloaded 

     Parameters:
     -----------
     1) pkg_name:    (str)  The name of the ggd package to get the .tar.bz2 file for
     2) jdict:       (dict) A metadata json dict for the ggd channel
     3) ggd_channel: (str)  The ggd channel where the package is
     4) prefix:      (str)  The full path of the conda environment/prefix to download the file to


    Returns:
    ++++++++
    1) (str) The install "pkg" dir for the conda environment where the tar file was downloaded
    2) (str) The tar file name
    3) (str) The file path of the downloaded tar file
    """

    channel_key = "ggd-%s" %ggd_channel
    
    ## Get the pkg names and tar files for each ggd package in the specific channel
    repodata_dict, name2tar = get_repodata(channels = [channel_key])

    assert (pkg_name in jdict["packages"]), ":ggd:meta-recipe: !!ERROR!! Could not find the {} data package in the repodata".format(pkg_name)

    matching_version = float(jdict["packages"][pkg_name]["version"])
    highest_build = float(-1)
    newest_tar = ""
    platform = ""

    ## Find the latest verion-build tar file
    for subdir in name2tar[channel_key].keys():
        
        if pkg_name in name2tar[channel_key][subdir]:

            for pkg_tar in name2tar[channel_key][subdir][pkg_name]:

                repo_version = float(repodata_dict[channel_key][pkg_tar]["version"])
                repo_build_number = float(repodata_dict[channel_key][pkg_tar]["build_number"])

                ## Check for a matching version and latest build
                if repo_version == matching_version and repo_build_number > highest_build:
                    
                    highest_build = repo_build_number
                    platform = subdir
                    newest_tar = pkg_tar

    ## Remove the repodata files
    del repodata_dict
    del name2tar

    ## Get the url for the tar file
    download_url = "https://anaconda.org/ggd-{channel}/{pkg_name}/{version}/download/{platform}/{tar_file}".format(channel = ggd_channel,
                                                                                                                    pkg_name = pkg_name,
                                                                                                                    platform = platform,
                                                                                                                    version = int(matching_version),
                                                                                                                    tar_file = newest_tar
                                                                                                                    )

    ## Check the info identiifed 
    assert (highest_build != -1.0), "\n:ggd:meta-recipe: !!ERROR!! Could not find the recipe in the repodata"

    assert (platform != ""), "\n:ggd:meta-recipe: !!ERROR!! Package not found in available platforms"

    assert (newest_tar != ""), "\n:ggd:meta-recipe: !!ERROR!! Unable to find the tar file"

    ## Check the tar file for matching name, version, and build
    assert(newest_tar == "{}-{}-{}.tar.bz2".format(pkg_name, 
                                                   int(matching_version), 
                                                   int(highest_build))
           ), "\n:ggd:meta-recipe: !!ERROR!! The tar file identified from the repodata does not match with the right version and build for this recipes. tar file: '{}', latest version-build '{}-{}'".format(newest_tar, int(matching_version), int(highest_build))

    

    ## Download dir: The pkgs directory in the designated install prefix
    dest_dir = os.path.join(prefix, "pkgs")

    ## Remove previous download
    if os.path.exists(os.path.join(dest_dir, newest_tar)):
        os.remove(os.path.join(dest_dir, newest_tar))
    

    ## Download the tar file
    print("\n:ggd:meta-recipe: Downloading meta-recipe package from conda to: '{}\n".format(dest_dir))

    try:
        sp.check_call(["wget", download_url, "--directory-prefix", dest_dir])
    except sp.CalledProcessError as e:
        print("\n:ggd:meta-recipe: !!ERROR!! in downloading the meta-recipe package from the Anaconda Cloud")
        print(str(e))
        sys.exit(1)

    ## Check that the exists in the target dir
    target_path = os.path.join(dest_dir,newest_tar) 
    assert (os.path.exists(target_path) and os.path.isfile(target_path)), "\n:ggd:meta-recipe: !!ERROR!! There was a problem downloading the meta-recipe pkg. It is missing from the target dir"

    print("\n:ggd:meta-recipe: Successfully downloaded {} to {}".format(newest_tar, dest_dir))

    return(dest_dir, newest_tar,  target_path)


def create_tmp_meta_recipe_env_file():
    """
    create_tmp_meta_recipe_env_file
    ===============================
    Method to create a tmp directory where the ID specific environment variables will be stored. The tmp dir is created,
     and the path to the meta-recipe json file is returned. Meta-recipes wishing to update the metadata for the ID specific 
     recipe should write to file path returend from this method. 

    NOTE: This tmp dir will persist and needs to be removed by the function that calls it once the use of it is complete. 

    Returns:
    ++++++++
    1) (str) The dir path to the tmp dir created
    2) (str) The file path of the json file in the tmp dir that should be created. 
    3) (str) The file path of the a bash file in the tmp dir that should be created which will contain any updated commands. 
    """
    import tempfile

    ## create tmp directory
    tmp_dir = tempfile.mkdtemp()

    ## CHeck the tmp dirs
    assert os.path.exists(tmp_dir), "\n:ggd:meta-recipe: !!ERROR!! There was a problem creating the temporary directory for meta-recipe enviornment variables" 
    assert os.access(tmp_dir, os.R_OK), "\n:ggd:meta-recipe: !!ERROR!! The temporary directory created for the meta-recipe environment variables is not readable"
    assert os.access(tmp_dir, os.W_OK), "\n:ggd:meta-recipe: !!ERROR!! The temporary directory created for the meta-recipe environment variables is not writeable"

    return(tmp_dir, os.path.join(tmp_dir,GGD_META_RECIPE_ENV_JSON), os.path.join(tmp_dir,GGD_META_RECIPE_FINAL_COMMANDS))


def extract_metarecipe_recipe_from_bz2(metarecipe_name,new_name,bz2_file_path):
    """
    extract_metarecipe_recipe_from_bz2
    ===================================
    Method to update a recipe from a .tar.bz2 package file when installing a metarecipe. The name of the main 
     metarecipe will be changed to the ID specific recipe name. (Example meta-recipe-geo-accession-geo-v1 => GSE123-geo-v1)

    The recipe will be a normal recipe directory and will be hosted in the tmp dir

    Once finished with the recipe it is advicesed to delete the tmp dir

    Parameters:
    -----------
    1) metarecipe_name: (str) The main name of the metarecipe
    2) new_name:        (str) The new/specific name of the ID specific recipe (The ID used when installing the metarecipe)
    3) bz2_file_path:   (str) THe file path of the metarecipe main tar.bz2 file

    Returns:
    ++++++++
    1) (Bool) True if successfully create the recipe dir else False
    2) (str)  The file path of the tmp dir recipe (None if not Successful)
    3) (str)  The file path of the tmp dir (None if not Successful)
    """
    
    print("\n:ggd:meta-recipe: Updating meta-recipe with ID info")

    import tempfile
    import tarfile

    ## create tmp directory
    tmp_dir = tempfile.mkdtemp()

    try:
        ## Extract all files in the tarfile to "ggd_tmp"
        with tarfile.open(bz2_file_path) as archive:
            archive.extractall(tmp_dir)
    except Exception as e:
        print("\n:ggd:ERROR: Unable to read {} as a tarfile".format(bz2_file_path))
        print(str(e))
        shutil.rmtree(tmp_dir)
        return(False, None, None)


    ## New/Update ID specific recipe path
    new_recipe_path = os.path.join(tmp_dir,new_name)
    if os.path.exists(new_recipe_path):
        shutil.rmtree(new_recipe_path)
    os.makedirs(new_recipe_path)


    ## Walk through a directory structure and extract the recipe
    for dir_path, dir_names, file_names in os.walk(tmp_dir):
        if "recipe" in dir_path:
            for name in file_names:
                ## SKip the conda build confg
                if name != "conda_build_config.yaml" and name != "meta.yaml":
                    shutil.move(os.path.join(dir_path,name), os.path.join(new_recipe_path,name.replace(".template","")))


    ## Walk through new recipe and rename files and content
    for dir_path, dir_names, file_names in os.walk(new_recipe_path):
        if file_names:
            for name in file_names:

                ## Get file path
                file_path = os.path.join(dir_path, name)

                ## Check file contents
                update_file = False
                file_contents = []
                if os.path.isfile(file_path):
                    try:
                        with open(file_path) as fh: 
                            for line in fh: 

                                if metarecipe_name in line:
                                    update_file = True
                                    file_contents.append(line.replace(metarecipe_name,new_name))
                                else:
                                    file_contents.append(line)
                    except IOError as e:
                        print("\n:ggd:ERROR: Unable to open archive file: {}".format(file_path))
                        print(str(e))
                        shutil.rmtree(tmp_dir)
                        return(False, None, None)

                if update_file:
                    #print("Update file: {}".format(file_path))
                    try:
                        with open(file_path, "w") as fh: 
                            for line in file_contents:
                                fh.write(line)
                    except IOError as e:
                        print("\n:ggd:ERROR: Unable to open archive file: {}".format(file_path))
                        print(str(e))
                        shutil.rmtree(tmp_dir)
                        return(False, None, None)

                ## Check file name
                if metarecipe_name in name:
                    #print("Change file name of {} to {}".format(file_path, file_path.replace(metarecipe_name,new_name)))
                    os.rename(file_path, file_path.replace(metarecipe_name,new_name))
        
    return(True, new_recipe_path, tmp_dir)


def update_metarecipe_metadata(pkg_name,env_var_dict, parent_name, final_file_list, final_file_size_dict, commands_str, prefix = None):
    """
    update_metarecipe_metadata
    ==========================
    Method to update a the metadata of an ID specific meta-recipe tar .bz2 package file.  
     
    The bz2 file will be creating th the tmp direcotry and be moved to the same directory path as the original bz2 file.

    The tmpdir of the file system will be used to create the new bz2 file

    Metadata is updated based on "envrionment variables" created during the meta-recipe installation sorted in a dict.

    Available Meta-Recipe Environment Variables that can be used to update the metadata include:
        - GGD_METARECIPE_SUMMARY:                   A summary of the installed data
        - GGD_METARECIPE_SPECIES:                   The speciecs of the installed data 
        - GGD_METARECIPE_GENOME_BUILD:              The genome build of the installed data
        - GGD_METARECIPE_VERSION:                   The version of the data installed
        - GGD_METARECIPE_KEYWORDS:                  A comma seperated list of key words to add to the metadata
        - GGD_METARECIPE_DATA_PROVIDER:             The data provider of the recipe. (Should already exists. Should not be used)
        - GGD_METARECIPE_FILE_TYPE:                 A comma seperated list of file types for the files installed by the package
        - GGD_METARECIPE_GENOMIC_COORDINATE_BASE:   A string that reperesnted the coordinate base of the installed files  

    The metadata sections will be updated only if the Environment Variables have been set in the dict

    Parameters:
    -----------
    1) pkg_name:             (str)  The name of the ID specific meta-recipe package 
    2) env_var_dict:         (dict) A dictionary of meta-recipe environment variables and their values
    3) parent_name:          (str)  The name of the parent meta-recipe
    4) final_file_list:      (list) A list of the final data files installed by the meta-recipe
    5) final_file_size_dict: (dict) A dictionary of installed files and the size of thoes files
    6) commands_str:         (str)  A string that represents the subsetted commands used by the ID specific meta-recipe
    7) prefix:               (str)  The conda environment/prefix to update. (Default = the current conda environment)

    Returns:
    ++++++++
    1) (bool) True if successfully updated the .tar.bz2 file else False
    2) (str)  The file path of the new bz2 file
    """

    print("\n:ggd:meta-recipe: Updating meta-recipe package metadata")

    import tempfile
    import tarfile
    import yaml

    ## Check prefix
    if prefix == None:
        prefix = conda_root()
    else:
        prefix_in_conda(prefix)

    ## Get bz2 file path
    pkg_list = get_conda_package_list(prefix = prefix, regex = pkg_name, include_local=True)

    ## bze file path is installed into the conda root path even if installing into a prefix. 
    pkg_dir = os.path.join(conda_root(), "pkgs")

    if pkg_name not in pkg_list:
        print("\n:ggd:meta-recipe: !!ERROR!! Package {} was not installed correctly. Package missing from the conda index".format(pkg_name))
        return(False, None)

    bz2_file_path = os.path.join(pkg_dir, "{}-{}-{}.tar.bz2".format(pkg_name, pkg_list[pkg_name]["version"], pkg_list[pkg_name]["build"]))

    ## create tmp directory
    tmp_dir = tempfile.mkdtemp()

    try:
        ## Extract all files in the tarfile to "ggd_tmp"
        with tarfile.open(bz2_file_path) as archive:
            archive.extractall(tmp_dir)
    except Exception as e:
        print("\nggd:meta-recipe: !!ERROR!! Unable to read {} as a tarfile".format(bz2_file_path))
        print(str(e))
        return(False, None)

    ## Walk through a directory structure
    for dir_path, dir_names, file_names in os.walk(tmp_dir):
        if file_names:
            for name in file_names:
                
                ## Update the recipe.sh file
                if name == "recipe.sh" and commands_str != "":
                    
                    try:
                        with open(os.path.join(dir_path,name),"w") as r_fh:
                            r_fh.write(commands_str)
                    except IOError as e:
                        print(":ggd:meta-recipe: !!ERROR!! Problem updating the recipe.sh file")
                        print(str(e))
                        return(False, None)

                
                ## Update the yaml files
                if "meta.yaml" in name:
                    ## Get file path
                    file_path = os.path.join(dir_path, name)
                    
                    metadata = yaml.safe_load(open(os.path.join(dir_path,name)))

                    ## Set the name of the parent meta-recipe 
                    metadata["about"]["identifiers"]["parent-meta-recipe"] = parent_name

                    ## Add final file list
                    metadata["about"]["tags"]["final-files"] = final_file_list

                    ## Add final file sizes
                    metadata["about"]["tags"]["final-file-sizes"] = final_file_size_dict

                    ## Check for available keys to change
                    if "GGD_METARECIPE_SUMMARY" in env_var_dict:
                        metadata["about"]["summary"] = env_var_dict["GGD_METARECIPE_SUMMARY"]

                    if "GGD_METARECIPE_SPECIES" in env_var_dict:
                        metadata["about"]["identifiers"]["updated-species"] = env_var_dict["GGD_METARECIPE_SPECIES"]

                    if "GGD_METARECIPE_GENOME_BUILD" in env_var_dict:
                        metadata["about"]["identifiers"]["updated-genome-build"] = env_var_dict["GGD_METARECIPE_GENOME_BUILD"]

                    if "GGD_METARECIPE_VERSION" in env_var_dict:
                        metadata["about"]["tags"]["data-version"] = env_var_dict["GGD_METARECIPE_VERSION"]

                    if "GGD_METARECIPE_KEYWORDS" in env_var_dict:
                        metadata["about"]["keywords"] += [x.strip() for x in env_var_dict["GGD_METARECIPE_KEYWORDS"].strip().split(",")]

                    if "GGD_METARECIPE_DATA_PROVIDER" in env_var_dict:
                        print((":ggd:meta-recipe: WARNING: The data provider is being updated from {} to {}."
                              " We recommend that Meta-Recipes do not change the data provider. If the"
                              " Data Provider does need to be changed, consider making a difference recipe" 
                              " for that Data Provider").format(metadata["about"]["tags"]["data-provider"], env_var_dict["GGD_METARECIPE_DATA_PROVIDER"]))
                        metadata["about"]["tags"]["data-provider"] = env_var_dict["GGD_METARECIPE_DATA_PROVIDER"]
                        
                    if "GGD_METARECIPE_FILE_TYPE" in env_var_dict:
                        metadata["about"]["tags"]["file-type"] = [x.strip() for x in env_var_dict["GGD_METARECIPE_FILE_TYPE"].strip().split(",")]

                    if "GGD_METARECIPE_GENOMIC_COORDINATE_BASE" in env_var_dict:
                        metadata["about"]["tags"]["genomic-coordinate-base"] = env_var_dict["GGD_METARECIPE_GENOMIC_COORDINATE_BASE"]

                    ## Write the new file
                    try:
                        with open(file_path, "w") as fh: 
                            fh.write(yaml.dump(metadata, default_flow_style=False))
                    except IOError as e:
                        print("\n:ggd:ERROR: Unable to write meta.yaml file: {}".format(file_path))
                        print(str(e))
                        return(False, None)


    cwd = os.getcwd()
    os.chdir(tmp_dir)

    bz2_file_name = os.path.basename(bz2_file_path)

    ## create new tarfile with updated info
    try:
        with tarfile.open(bz2_file_name, "w:bz2") as archive:

            for dir_path, dir_names, file_names in os.walk("./"):
                if file_names:
                    for name in file_names:
                        file_path = os.path.join(dir_path, name).replace("./","")
                        archive.add(file_path)
    except Exception as e:
        print("\n:ggd:meta-recipe: !!ERROR!! Unable to create .tar.bz2 file: {}".format(bz2_file_path))
        print(str(e))
        return(False, None)

    os.chdir(cwd)
        
    ## Move new tar file to new location
    try:
        shutil.move(os.path.join(tmp_dir,bz2_file_name),bz2_file_path)
    except Exception as e:
        print("\n:ggd:ERROR: Unable to move new tar file to bz2 location")
        print(str(e))
        return(False, None)

    ## Remove tmp dir
    shutil.rmtree(tmp_dir)

    return(True, bz2_file_path)


def get_conda_package_list(prefix, regex=None, include_local=False):
    """
    This method is used to get the list of packages in a specific conda environment (prefix). Rather then running 
     `conda list` itself, it uses the conda module to grab the information 

    
    Parameters:
    -----------
    1) prefix:        (str)  The directory path to a conda environment in which you would like to extract the ggd data packages that have been installed
    2) regex:         (str)  A pattern to match to (default = None)
    3) include_local: (bool) True or False, whether to include the local channel. (Default = False)

    Returns:
    +++++++
    1) (dict) A dictionary with the package name as a key, and the value as another dictionary with name, version, build, and channel keys
    """

    from logging import getLogger

    from conda.base.context import context
    from conda.cli.main_list import get_packages
    from conda.core.prefix_data import PrefixData
    from conda.gateways import logging

    ## Get a list of available ggd channels
    ggd_channels = ["ggd-" + x for x in get_ggd_channels()]

    if include_local:
        ggd_channels = ggd_channels + ["local"]

    ## Get a prefix data object with installed package information
    installed_packages = sorted(
        PrefixData(prefix).reload().iter_records(), key=lambda x: x.name
    )

    ## Create a dictionary with ggd packages
    package_dict = {}
    for precs in get_packages(installed_packages, regex):
        ## If a file is installed locally, but from a different prefix it will have the file path rather then the "local" channel
        ### If "file: is seen, treat it as a local channel file
        precs_channel = "local" if "file:" in str(precs.schannel) else str(precs.schannel)
        if (
            precs_channel in ggd_channels
        ):  ## Filter based on packages from the ggd channels only (or local file system if designated)
            package_dict[precs.name] = {
                "name": precs.name,
                "version": precs.version,
                "build": precs.build,
                "channel": precs.schannel,
            }

    return package_dict


def get_meta_recipe_checksum(meta_recipe_name, id_specific_name, file_name = "checksums.json"):
    """
    get_meta_recipe_checksum
    ========================
    Method to get the checksum values for specific files of an id specific recipe installed from a meta-recipe.
     If checksum values exists, a dict with file name and checksum value will be returned. If no checksum values 
     exists an empty dict is returned. 

    Parameters:
    -----------
    1) meta_recipe_name: (str) Name of the meta-recipe 
    2) id_specific_name: (str) Name of the id specific recipe installed from the meta-recipe
    3) file_name:        (str) Name of the file to load. Default = checksums.json

    Returns:
    ++++++++
    1) (dict) Checksum values for the files of the id specific recipe or an empty dict if no checksum values exists
    """
    try:
        checksum_dict = requests.get(GGD_META_RECIPE_URL.format(meta_recipe_name = meta_recipe_name,
                                                                file_name = file_name)).json()
    except ValueError as e:
        print("\n:ggd:meta-recipe: !!ERROR!! There was a problem loading the checksum file for the meta-recipe: {}".format(meta_recipe_name))
        print(str(e))
        sys.exit(1)

    if id_specific_name in checksum_dict:
        return(checksum_dict[id_specific_name])
    else:
        return(dict())


def get_file_md5sum(file_path):
    """Method to get the the md5sum of a file 

    get_file_md5sum
    ===============
    Method to get the md5sum of the contents of a file for use in checksum. 

    To reduce potential problems with in-memory storage of a file, the file is read in 4096 bytes 
     at a time and the checksum is updated each iterate of 4096 byte reads. 

    Parameters:
    -----------
    1) file_path: (str) The full file path, including the file name, of the file to get the checksum for

    Returns:
    ++++++++
    1) (str) The hexidecimal md5sum encoding for the contents of the file

    """
    import hashlib

    md5sum = hashlib.md5()
    with open(file_path, "rb") as f:
        ## Iterate over a chunk size of 4096 bytes to reduce in-memory problems
        for chunk in iter(lambda: f.read(4096), b""):
            md5sum.update(chunk)

    return md5sum.hexdigest()


def get_checksum_dict_from_txt(txt_file_path):
    """Method used to get the checksum file from a ggd recipe  

    get_checksum_dict_from_txt
    ===================
    This method is used to obtain a ggd recipe's checksum file from the recipes checksum_file.txt.

    Parameters:
    ----------
    1) txt_file_path: (str) The file path to the recipe's checksums file
    
    Return:
    +++++++
    1) (dict) The checksum file as a dictionary. Key = filename, value = md5sum for the file 
    """

    cs_dict = {}
    with open(txt_file_path, "r") as cs:
        for line in cs:
            line_list = str(line).strip().split("\t")
            ## Skip empty lines
            if len(line_list) < 2:
                continue
            cs_dict[line_list[0]] = line_list[1]

    return cs_dict


def get_checksum_dict_from_tar(fbz2):
    """Method used to get the checksum file from a ggd package that has been built and is in a tar.bz2 file format

    get_checksum_dict_from_tar
    ===================
    This method is used to obtain a ggd recipe's checksum file from an already built ggd package.

    Parameters:
    ----------
    1) fbz2: (str) The file path to the pre-built bz2 ggd package
    
    Return:
    +++++++
    1) (dict) The checksum file as a dictionary. Key = filename, value = md5sum for the file 
    """
    import tarfile

    info = None
    with tarfile.open(fbz2, mode="r|bz2") as tf:
        for info in tf:  ## For/else
            if info.name == ("info/recipe/checksums_file.txt"):
                break
        else:
            print(":ggd:checksum: !!Error!!: Incorrect tar.bz format.", file=sys.stderr)
            exit(1)

        checksum_file = tf.extractfile(info)
        cs_dict = {}
        for line in str(checksum_file.read().decode("utf8")).strip().split("\n"):
            line_list = str(line).strip().split("\t")
            ## Skip empty lines
            if len(line_list) < 2:
                continue
            cs_dict[line_list[0]] = line_list[1]

    return cs_dict


def data_file_checksum(installed_dir_path, checksum_dict):
    """Method to check a recipe's data file md5sum checksums against the installed data file md5sums checksum 

    data_file_checksum
    ===================
    Method to compare the md5sum checksum for installed data files from a data package against the 
     md5sum checksum values in the recipe data. An ERROR will be printed if checksum fails, as well as 
     the method will return False.

    Parameters:
    -----------
    1) installed_dir_path: (str)  The directory path to the installed data files
    2) checksum_dict:      (dict) A dictionary with md5sum checksum values for each file for the data package stored in the recipe

    Returns:
    +++++++
    1) (bool) True if checksum passes, False if otherwise
    """
    import glob

    ## Get a list of the installed data files
    installed_files = glob.glob(os.path.join(installed_dir_path, "*"))

    ## Check that there are the same number of installed data files as files with original checksums
    if len(installed_files) != len(checksum_dict):
        print(
            "\n\n:ggd:checksum: !!ERROR!! The number of installed files does not match the number of checksum files"
        )
        print(
            ":ggd:checksum: Installed files checksum  (n = {n}): {f}".format(
                n=len(installed_files),
                f=", ".join([os.path.basename(x) for x in installed_files]),
            )
        )
        print(
            ":ggd:checksum: Metadata checksum record  (n = {n}): {f}".format(
                n=len(checksum_dict), f=", ".join(checksum_dict.keys())
            )
        )
        return False

    ## Check each installed data file against the recipe's checksum
    for ifile in installed_files:
        ifile_name = os.path.basename(ifile.rstrip("/"))

        ## Check that the file exists in the checksum
        if ifile_name not in checksum_dict.keys():
            print(
                "\n\n:ggd:checksum: !!ERROR!! The installed file {f} is not one of the checksum files\n".format(
                    f=ifile_name
                )
            )
            return False

        ## Check md5sum
        ifile_md5sum = get_file_md5sum(ifile)
        print(
            ":ggd:checksum: installed  file checksum:",
            os.path.basename(ifile),
            "checksum:",
            ifile_md5sum,
        )
        print(
            ":ggd:checksum: metadata checksum record:",
            ifile_name,
            "checksum:",
            checksum_dict[ifile_name],
            "\n",
        )
        if ifile_md5sum != checksum_dict[ifile_name]:
            print(
                "\n\n:ggd:checksum: !!ERROR!! The {f} file's checksums don't match, suggesting that the file wasn't installed properly\n".format(
                    f=ifile_name
                )
            )
            return False

    return True


def get_file_size(file_path):

    import math

    if os.path.exists(file_path):

        ## Range size
        range_size = 0.05

        ## Get size of file in bytes
        bytes_size = os.path.getsize(file_path)

        ## Convert size to gb, mb, kb
        ## Use the rough equal numbers. (Over estimate rather than under estimate)
        gb_size = bytes_size / (
            1000000000
        )  # (1073741824) ## bytes in a GB = (1024 * 1024 * 1024) = 1073741824 ~~ 1000000000
        mb_size = bytes_size / (
            1000000
        )  # (1048576) ## Bytes in a MB = (1024*1024) = 1048576 ~~ 1000000
        kb_size = bytes_size / (1000)  # (1024) ## Bytes in a KB = (1024) ~~ 1000

        final_size = ""
        ## Format the file size
        if gb_size >= 1.0:
            final_size = "{:.2f}G".format(gb_size)

            ## Get top actual and bottom size range using 5% of actual size
            top_size = (bytes_size + (bytes_size * range_size)) / (1000000000)
            bottom_size = (bytes_size - (bytes_size * range_size)) / (1000000000)

        elif mb_size >= 1.0:
            final_size = "{:.2f}M".format(mb_size)

            ## Get top actual and bottom size range using 5% of actual size
            top_size = (bytes_size + (bytes_size * range_size)) / (1000000)
            bottom_size = (bytes_size - (bytes_size * range_size)) / (1000000)

        elif kb_size >= 1.0:
            final_size = "{:.2f}K".format(kb_size)

            ## Get top actual and bottom size range using 5% of actual size
            top_size = math.ceil((bytes_size + (bytes_size * range_size)) / (1000))
            bottom_size = math.floor((bytes_size - (bytes_size * range_size)) / (1000))

        else:
            final_size = "{:.2f}b".format(bytes_size)

            ## Get top actual and bottom size range using 5% of actual size
            top_size = bytes_size + (bytes_size * range_size)
            bottom_size = bytes_size - (bytes_size * range_size)

        ## Return final_size as a string, top of size window ,and bottom of size window
        return (final_size, top_size, bottom_size)

    else:
        print("\n:ggd:utils: File does not exist: {fp}\n".format(fp=file_path))

        return None


def bypass_satsolver_on_install(
    pkg_names, conda_channel="ggd-genomics", debug=False, prefix=None
):
    """Method to bypass the sat solver used by conda when a cached recipe is being installed

    bypass_satsolver_on_install
    ============================
    This method is used to run the conda install steps to install a ggd aws cached recipe. The
        installation will skip the sat solver step, ignore packages that may be additionally installed
        or uninstalled, and performs other steps in order to install the data package without using 
        the sat solver. 
    The majority of the work is still done by conda through the use of the conda module. This method
        should only be used when a cached recipe is being installed.

    Parameters:
    -----------
    1) pkg_names:     (list) A list of the names of the ggd packages to install. (Example: [hg19-gaps])
    2) conda_channel: (str)  The ggd conda channel that package is being installed from. (Example: ggd-genomics)
    3) debug:         (bool) Whether or not to set logging to debug 
    4) prefix:        (str)  The prefix to install the pkgs into
    """

    # -------------------------------------------------------------------------
    # import statements
    # -------------------------------------------------------------------------
    import sys
    from argparse import Namespace
    from logging import (
        DEBUG,
        ERROR,
        INFO,
        WARN,
        Filter,
        Formatter,
        StreamHandler,
        getLogger,
    )

    from conda._vendor.boltons.setutils import IndexedSet
    from conda._vendor.toolz import concat, concatv
    from conda.base.constants import UpdateModifier
    from conda.base.context import context
    from conda.cli import common, install
    from conda.common.compat import iteritems, itervalues, odict, text_type
    from conda.common.io import ProgressBar, Spinner
    from conda.core.link import PrefixSetup, UnlinkLinkTransaction
    from conda.core.solve import (
        Solver,
        SolverStateContainer,
        diff_for_unlink_link_precs,
    )
    from conda.gateways.logging import (
        VERBOSITY_LEVELS,
        log,
        set_all_logger_level,
        set_conda_log_level,
    )
    from conda.models.match_spec import MatchSpec
    from conda.models.prefix_graph import PrefixGraph
    from conda.resolve import Resolve

    print(
        "\n:ggd:utils:bypass: Installing %s from the %s conda channel\n"
        % (", ".join(pkg_names), conda_channel)
    )

    # -------------------------------------------------------------------------
    # Nested functions
    # -------------------------------------------------------------------------
    # def bypass_sat(package_name,ssc_object): ## Package_name will be used as a key
    def bypass_sat(package_names, ssc_object):  ## Package_name will be used as a key
        """Method used to extract information during sat solving, but to bypass the sat solving step

        bypass_sat
        ==========
        This method is used to extract and process information that would have been done during the sat
        solving step, (Solving Environment), bypass the sat solver, and return a filtered set of packages
        to install.

        Parameters:
        -----------
        #1) package_name: (str)  The name of the package to extract. (This is the package that will be installed)
        1) package_names: (list) A list of package names of the packages to extract. (This is the package that will be installed)
        2) ssc_object:    (SolverStateContainer Object)  processed conda SolverStateContainer object. 

        Returns:
        +++++++
        1) (SolverStateContainer Object) The updated ssc object based off the sat bypass and package filtering. 

        """

        ## From Solver.run_sat
        specs_map_set = set(itervalues(ssc_object.specs_map))

        ## Get the specs from ssc filtered by the package name
        new_odict = odict(
            [(p_name, ssc_object.specs_map[p_name]) for p_name in package_names]
        )
        final_environment_specs = IndexedSet(
            concatv(
                itervalues(new_odict),
                ssc_object.track_features_specs,
                ssc_object.pinned_specs,
            )
        )

        ## Run the resolve process and get info for desired package
        ssc_object.solution_precs = ssc_object.r.solve(tuple(final_environment_specs))

        wanted_indices = []
        for i, info in enumerate(ssc_object.solution_precs):
            for p_name in package_names:
                if p_name in ssc_object.solution_precs[i].namekey:
                    wanted_indices.append(i)

        filtered_ssc_solution_precs = [
            ssc_object.solution_precs[x] for x in wanted_indices
        ]
        ssc_object.solution_precs = filtered_ssc_solution_precs

        ## Add the final environment specs to ssc
        ssc_object.final_environment_specs = final_environment_specs

        return ssc_object

    # -------------------------------------------------------------------------
    # Run install
    # -------------------------------------------------------------------------

    ## Set the context.always_yes to True to bypass user input
    context.always_yes = True

    target_prefix = context.target_prefix if prefix == None else prefix

    # Setup solver object
    # solve = Solver(target_prefix, (conda_channel,u'default'), context.subdirs, [pkg_name])
    solve = Solver(
        target_prefix, (conda_channel, u"default"), context.subdirs, pkg_names
    )

    ## Create a solver state container
    ### Make sure to Freeze those packages already installed in the current env in order to bypass update checking.
    ssc = SolverStateContainer(
        prefix=target_prefix,
        update_modifier=UpdateModifier.FREEZE_INSTALLED,
        deps_modifier=context.deps_modifier,
        prune=True,
        ignore_pinned=context.ignore_pinned,
        force_remove=context.force_remove,
        should_retry_solve=False,
    )

    ## Get channel metadata
    with Spinner(
        "Collecting package metadata",
        not context.verbosity and not context.quiet,
        context.json,
    ):
        ssc = solve._collect_all_metadata(ssc)

    ## Set specs map to an empty map. (No need to check other specs)
    add_spec = []
    for p_name, spec in iteritems(ssc.specs_map):
        for pkg_name in pkg_names:
            if str(p_name) in pkg_name:
                add_spec.append((pkg_name, MatchSpec(pkg_name)))

    ssc.specs_map = odict(add_spec)

    ## Process the data in the solver state container
    with Spinner(
        "Processing data", not context.verbosity and not context.quiet, context.json
    ):
        ssc = solve._add_specs(ssc)
        ssc = bypass_sat(pkg_names, ssc)
        ssc = solve._post_sat_handling(ssc)

    ## create an IndexedSet from ssc.solution_precs
    ssc.solution_precs = IndexedSet(PrefixGraph(ssc.solution_precs).graph)

    ## Get linked and unlinked
    unlink_precs, link_precs = diff_for_unlink_link_precs(
        target_prefix, ssc.solution_precs, solve.specs_to_add
    )

    # set unlinked to empty indexed set so we do not unlink/remove any packages
    unlink_precs = IndexedSet()

    ## Create a PrefixSetup
    stp = PrefixSetup(
        solve.prefix,
        unlink_precs,
        link_precs,
        solve.specs_to_remove,
        solve.specs_to_add,
        solve.neutered_specs,
    )

    ## Create an UnlinkLinkTransaction with stp
    unlink_link_transaction = UnlinkLinkTransaction(stp)

    # create Namespace
    args = Namespace(
        channel=None,
        cmd="install",
        deps_modifier=context.deps_modifier,
        json=False,
        packages=pkg_names,
    )

    ## Set logger level
    if debug:
        WARN, INFO, DEBUG, TRACE = VERBOSITY_LEVELS
        set_all_logger_level(DEBUG)

    ## Install package
    install.handle_txn(unlink_link_transaction, solve.prefix, args, False)

    ## Return True if finished
    return True


if __name__ == "__main__":
    import doctest

    doctest.testmod()
