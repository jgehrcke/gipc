#!/bin/bash
set -ex


python setup.py check
python setup.py --long-description | rst2html5 > /dev/null
rst2html5 CHANGELOG.rst > /dev/null

# Run flake8 on the gipc directory (do not yet
# run on examples and test code).
flake8 gipc/

# The pylint result is not to be interpreted in a binary fashion.
# pylint --reports=n --disable=C0103,W0212,W0511,W0142,R0903 gipc/gipc.py

# Build documentation.
cd docs && make html && cd ..

# See if this would be good to release.
pip install twine==5.1.1
rm -rf dist
python setup.py sdist
twine check dist/*
