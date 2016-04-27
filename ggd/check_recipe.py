from __future__ import print_function
import sys
import os
import os.path as op
import tarfile
import re
from fnmatch import fnmatch

import subprocess as sp
import yaml

if sys.version_info[0] < 3:
    import urllib
    urlopen = urllib.urlopen
else:
    from urllib.request import urlopen

def list_files(dir):
    rfiles = []
    subdirs = [x[0] for x in os.walk(dir)]
    for subdir in subdirs:
        files = os.walk(subdir).next()[2]
        if (len(files) > 0):
            for file in files:
                rfiles.append(op.join(subdir, file))
    return [(p, os.stat(p).st_mtime) for p in rfiles]


def add_check_recipe(p):

    c = p.add_parser('check-recipe', help="build, install, and check a recipe")
    c.add_argument("recipe_path", help="path to recipe directory (can also be path to the .bz2")
    c.set_defaults(func=check_recipe)


def conda_root():
    return sp.check_output(['conda', 'info', '--root']).strip()


def _build(path):
    out = sp.check_output(['conda', 'build', '--no-anaconda-upload', path], stderr=sys.stderr)
    upload = [x for x in out.split("\n") if "$ anaconda upload" in x]
    assert len(upload) == 1, upload
    bz2 = upload[0].split("upload ")[1].strip()
    return bz2


def _install(bz2):
    sp.check_call(['conda', 'install', bz2], stderr=sys.stderr,
                  stdout=sys.stdout)

def get_recipe_from_bz2(fbz2):
    info = None
    with tarfile.open(fbz2, mode="r|bz2") as tf:
        for info in tf:
            if info.name == "info/recipe/meta.yaml":
                break
        else:
            raise KeyError

        recipe = tf.extractfile(info)
        recipe = yaml.load(recipe.read().decode())
    return recipe

def _check_build(build):
    gf = "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/{build}/{build}.genome".format(build=build)
    try:
        ret = urlopen(gf)
        if ret.getcode() >= 400:
            raise Exception("%s at url: %s" % (ret.getcode(), gf))
    except:
        sys.stderr.write("ERROR: genome-build: %s not found in github repo.\n" % build)
        raise

def check_recipe(parser, args):
    if args.recipe_path.endswith(".bz2"):
        recipe = get_recipe_from_bz2(args.recipe_path)
        bz2 = args.recipe_path
    else:
        recipe = yaml.load(open(op.join(args.recipe_path, "meta.yaml")))
        bz2 = _build(args.recipe_path)
    species, build = check_yaml(recipe)

    _check_build(build)

    install_path = op.join(conda_root(), "share", "ggd", species, build)

    before = list_files(install_path)

    _install(bz2)

    check_files(install_path, species, build, recipe['package']['name'],
                recipe['extra'].get('extra-files', []), before)
    print("OK")

def get_modified_files(files, before_files):
    before_files = dict(before_files)
    files = [p for p, mtime in files if mtime > before_files.get(p, 0)]
    return files

def check_files(install_path, species, build, recipe_name,
                extra_files, before_files):
    P = "{species}/{build}:{recipe_name}".format(**locals())

    files = list_files(install_path)
    files = get_modified_files(files, before_files)
    if len(files) == 0:
        sys.stderr.write("ERROR: no modified files in %s\n" % install_path)
        sys.exit(2)
    print("modified files:\n\t :: %s\n\n" % "\n\t :: ".join(files))

    tbis = [x for x in files if x.endswith(".tbi")]
    nons = [x for x in files if not x.endswith(".tbi")]

    tbxs = [x[:-4] for x in tbis if x[:-4] in nons]

    nons = [x for x in nons if not x in tbxs]
    # check for fais?
    fais = [x for x in nons if x.endswith(".fai")]
    nons = [x for x in nons if not x in fais]
    fais = map(op.basename, fais)

    # ignore gzi
    nons = [n for n in nons if not n.endswith('.gzi')]

    gf = "https://raw.githubusercontent.com/gogetdata/ggd-recipes/master/genomes/{build}/{build}.genome".format(build=build)
    _check_build(build)

    for tbx in tbxs:
        print("> checking %s" % tbx)
        try:
            sp.check_call(['check-sort-order', '--genome', gf, tbx], stderr=sys.stderr)
        except sp.CalledProcessError as e:
            sys.stderr.write("ERROR: in: %s(%s) with genome sort order compared to that specified in genome file\n" % (P, tbx))
            sys.exit(e.returncode)

    missing = []
    not_tabixed = []
    not_faidxed = []
    for n in nons:
        print("> checking %s" % n)
        if n.endswith((".bed", ".bed.gz", ".vcf", ".vcf.gz", ".gff",
                       ".gff.gz", ".gtf", ".gtf.gz", ".gff3", ".gff3.gz")):

            not_tabixed.append("ERROR: with: %s(%s) must be sorted, bgzipped AND tabixed.\n" % (P, n))
        elif n.endswith((".fasta", ".fa", ".fasta.gz", ".fa.gz")):
            if not op.basename(n + ".fai") in fais and not (re.sub("(.+).fa(?:sta)?$",
                                                       "\\1",
                                                       op.basename(n)) + ".fai") in fais:
                not_faidxed.append("ERROR: with: %s(%s) fasta files must have an associated fai.\n" % (P, n))

        elif op.basename(n) not in extra_files and not any(fnmatch(op.basename(n), e) for e in extra_files):
                missing.append("ERROR: %s(%s) uknown file and not in the extra/extra-files section of the yaml\n" % (P, n))

    if missing or not_tabixed or not_faidxed:
        print("\n".join(missing + not_tabixed + not_faidxed), file=sys.stderr)
        sys.exit(2)



def check_yaml(recipe):

    assert 'extra' in recipe, ("must specify 'extra:' section with genome-build and species")
    assert 'genome-build' in recipe['extra'], ("must specify 'extra:' section with species")
    assert 'species' in recipe['extra'], ("must specify 'extra:' section with species")
    assert 'keywords' in recipe['extra'] and \
        isinstance(recipe['extra']['keywords'], list), ("must specify 'extra:' section with keywords")
    assert 'about' in recipe and 'summary' in recipe['about'], ("must specify an 'about/summary' section")

    species, build = recipe['extra']['species'], recipe['extra']['genome-build']

    _check_build(build)
    return species, build
