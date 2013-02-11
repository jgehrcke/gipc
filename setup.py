# -*- coding: utf-8 -*-
# Copyright 2012-2013 Jan-Philip Gehrcke. See LICENSE file for details.


# For packaging, I tried to follow these recommendations:
# http://guide.python-distribute.org/introduction.html#current-state-of-packaging
# http://pythonhosted.org/distribute/using.html
# http://ziade.org/2010/03/03/the-fate-of-distutils-pycon-summit-packaging-sprint-detailed-report/

import distribute_setup
distribute_setup.use_setuptools()
from setuptools import setup
from gipc import __version__ as gipcversion

setup(
    name = "gipc",
    packages = ["gipc"],
    py_modules = ["distribute_setup"],
    version = gipcversion,
    description = "gevent-cooperative child processes and inter-process communication.",
    long_description=open("README.rst").read().decode('utf-8'),
    author = "Jan-Philip Gehrcke",
    author_email = "jgehrcke@googlemail.com",
    url = "http://gehrcke.de/gipc",
    keywords = ["gevent", "multiprocessing", "ipc", "child processes"],
    platforms = ["POSIX", "Windows"],
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware :: Symmetric Multi-processing",
        ],
    #install_requires=("gevent>=1.0"), # currently not available at PyPI.
    )
