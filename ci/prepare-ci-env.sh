#!/bin/bash
set -x

if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then
    echo "Linux: use Travis-provides Python"
fi


if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
    echo "Use praekelt.org's setup-pyenv."
    export PYENV_RELEASE="v1.2.7"
    wget https://raw.githubusercontent.com/jgehrcke/travis-pyenv/develop/setup-pyenv.sh

    # This sets up the pyenv-provided Python in the _current_ shell. Do not exit
    # this shell, so that the `script` part in .travis.yml executes in the same
    # shell.
    source setup-pyenv.sh
fi

# Install gipc dependencies from its `setup.py`.
pip install .

# Install gipc test/CI dependencies.
pip install -r requirements-tests.txt

if [[ "$GEVENT_VERSION" != "default" ]]; then
    echo "Override gevent version to $GEVENT_VERSION"
    pip install "$GEVENT_VERSION" --upgrade
fi
