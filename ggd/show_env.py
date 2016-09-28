from __future__ import print_function
import os
from .check_recipe import check_output

def add_show_env(p):
    c = p.add_parser('show-env', help="show recipe variables available for this conda environment")
    c.add_argument("-p", "--pattern", help="regular expression pattern to match the name of the variable desired")
    c.set_defaults(func=show_env)

def show_env(parser, args): 
    pattern = args.pattern if args.pattern else "*"
    conda_env,conda_path = get_conda_env()
    env_filename = os.path.join(conda_path, "etc", "conda","activate.d","env_vars.sh")
    env_vars = set()
    try:
        with open(env_filename, "r") as env_file:
            for var in env_file:
                env_vars.add(var.strip().split()[1].split("=")[0])
        active_vars,inactive_vars = test_vars(env_vars)
        if len(active_vars) > 0:
            print ("Active environment variables:")
            for active_var in active_vars:
                print ("> $" + active_var)
            print()
        if len(inactive_vars) > 0:
            print ("Inactive environment variables:")
            for inactive_var in inactive_vars:
                print ("> $" + inactive_var)
            print ("\nTo activate inactive vars, run:\nsource activate %s\n" % conda_env)
    except IOError:
        print ("No recipe variables found for this environment")

def test_vars(env_vars):
    active_vars = []
    inactive_vars = []
    for env_var in env_vars:
        if env_var in os.environ and os.environ[env_var] != "":
            active_vars.append(env_var)
        else:
            inactive_vars.append(env_var)
    return active_vars,inactive_vars 

def get_conda_env():
    env_info = check_output(["conda", "info", "--envs"])
    fields = env_info.split("\n")
    curr_env = ""
    for field in fields:
        if len(field) > 0 and field[0] != "#":
            env = field.split()
            if len(env) > 0 and "*" in env:
                return env[0],env[-1]
    #TODO add exception and die here
