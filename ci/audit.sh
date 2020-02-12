#!/bin/bash
set -ex

# Do not run audit.sh as part of every build.

if [[ "$TRAVIS" == "true" ]]; then
    if [[ "$TRAVIS_PYTHON_VERSION" == "3.6" && "$TRAVIS_OS_NAME" == "linux" ]]; then
        echo "Linux and Python 3.6: run audit.sh"
    else
        echo "Do not run audit.sh: os: $TRAVIS_OS_NAME, python: $TRAVIS_PYTHON_VERSION"
        exit 0
    fi
fi

python setup.py check
python setup.py --long-description | rst2html.py > /dev/null
rst2html.py CHANGELOG.rst > /dev/null

# Run flake8 on the gipc directory (do not yet
# run on examples and test code).
flake8 gipc/

# The pylint result is not to be interpreted in a binary fashion.
# pylint --reports=n --disable=C0103,W0212,W0511,W0142,R0903 gipc/gipc.py

# Build documentation.
cd docs && make html && cd ..

# See if this would be good to release.
pip install twine==3.1.1
rm -rf dist
python setup.py sdist
twine check dist/*
