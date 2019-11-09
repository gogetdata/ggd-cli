from setuptools import setup
import re

with open('ggd/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

requires = ["pyyaml"]
setup(
    name="ggd",
    version=version,
    description="CLI for gogetdata (ggd)",
    long_description=open("README.md").read(),
    author="Michael Cormier, GGD Team",
    author_email="cormiermichaelj@gmail.com",
    url="https://github.com/gogetdata/ggd-cli",
    packages=['ggd', 'ggd.tests'],
    package_data={"": ['LICENSE', 'README.md']},
    package_dir={'ggd': 'ggd'},
    include_package_data=True,
    install_requires=requires,
    license='MIT',
    zip_safe=False,

    entry_points={
        'console_scripts': [
            'ggd = ggd.__main__:main'
        ]
    },

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics']
)
