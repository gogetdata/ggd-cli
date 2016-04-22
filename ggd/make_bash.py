
# TODO: get this by querying the git repo.
species = ('Homo_sapiens', 'Mus_musculus', 'Canis_familiaris')

def add_make_bash(p):
    c = p.add_parser('from_bash', help="make a new ggd/conda recipe give a bash script")
    c.add_argument("--species", help="species recipe is for", choices=species)
    c.add_argument("--genome-build", help="genome-build the recipe is for")
    c.add_argument("--dependency", default=[], action="append",
        help="any software dependencies (in bioconda, conda-forge) or data-dependency (in ggd)" +
        ". May be as many times as needed.")
    c.add_argument("--extra-file", default=[], action="append",
        help="any files that the recipe creates that are not a *.gz and *.gz.tbi pair. May be used more than once")
    c.add_argument("--summary", help="a comment describing the recipe")
    c.add_argument("--keyword", help="a keyword to associate with the recipe." +
        " may be specified more that once.", action="append", default=[])
    c.add_argument("script", help="bash script that contains the commands that build the recipe")

    c.set_defaults(func=make_bash)

def make_bash(parser, args):
    print(args)
