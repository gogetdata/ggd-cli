import requests

# TODO modified the branch for testing only
ENDPOINT= "https://api.github.com/repos/gogetdata/ggd-recipes/git/trees/structure-revision"

def get_species():
    """
    >>> get_species()
    [u'GRCh37', u'canFam3', u'dm3', u'dm6', u'hg19', u'hg38', u'mm10', u'mm9']
    """
    json = requests.get(ENDPOINT).json()
    tree = json['tree']
    genomes_url = next(t for t in tree if t['path'] == "genomes")['url']
    json = requests.get(genomes_url).json()
    return [x['path'].decode('ascii') for x in json['tree']]

if __name__ == "__main__":
    import doctest
    doctest.testmod()

