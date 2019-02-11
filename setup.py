# -*- coding: utf-8 -*-
# Copyright 2012-2018 Dr. Jan-Philip Gehrcke. See LICENSE file for details.

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
    long_description=open("README.rst", "rb").read().decode('utf-8'),
    author = "Jan-Philip Gehrcke",
    author_email = "jgehrcke@googlemail.com",
    url = "https://gehrcke.de/gipc",
    keywords = ["gevent", "multiprocessing", "ipc", "child processes"],
    platforms = ["POSIX", "Windows"],
    classifiers = [
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware :: Symmetric Multi-processing",
        "Intended Audience :: Developers",
        ],
    install_requires=("gevent>=1.2,<1.5"),
    )
