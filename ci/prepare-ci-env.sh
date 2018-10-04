#!/bin/bash
set -x


if [[ -z "${PYENV_VERSION}" ]]; then
    echo "Use Travis-provided Python"
else
    echo "Use praekelt.org's setup-pyenv."
    export PYENV_RELEASE="v1.2.7"
    wget https://raw.githubusercontent.com/jgehrcke/travis-pyenv/develop/setup-pyenv.sh

    # This sets up the pyenv-provided Python in the _current_ shell. Do not exit
    # this shell, so that the `script` part in .travis.yml executes in the same
    # shell.
    source setup-pyenv.sh
fi


if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then

    # https://github.com/jgehrcke/gipc/issues/56
    echo "ulimit -n: $(ulimit -n)"
    ulimit -n 1500
    echo "ulimit -n: $(ulimit -n)"

    # https://github.com/jgehrcke/gipc/issues/59
    # https://stackoverflow.com/a/21118126/145400
    # The Travis CI Mac environment has coreutils installed.
    export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"
fi


# Install newer pip and setuptools (newer than bundles with certain Python
# releases and newer than what Travis brings) -- but still pin the versions so
# that there are no moving dependencies.
pip install 'pip==18.0' --upgrade
pip install 'setuptools==40.4.3' --upgrade

# Install gipc dependencies from its `setup.py`.
pip install .

# Install gipc test/CI dependencies.
pip install -r requirements-tests.txt

if [[ "$GEVENT_VERSION" != "default" ]]; then
    echo "Override gevent version to $GEVENT_VERSION"
    pip install "$GEVENT_VERSION" --upgrade
fi
