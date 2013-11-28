# -*- coding: utf-8 -*-
# Copyright 2012-2013 Jan-Philip Gehrcke. See LICENSE file for details.

import re
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

gipcversion = re.search(
    "^__version__\s*=\s*'(.*)'",
    open('gipc/__init__.py').read(),
    re.M
    ).group(1)
assert gipcversion

setup(
    name = "gipc",
    packages = ["gipc"],
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
    install_requires=("gevent>=1.0"),
    )
