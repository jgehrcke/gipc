#!/bin/bash
set -o errexit
set -o errtrace
set -o pipefail
set -o xtrace


if [[ -z "${PYENV_PYTHON_VERSION}" ]]; then
    echo "Use Travis-provided Python"
else
    # Travis seems to set PYENV_ROOT to /opt/pyenv which holds an old pyenv
    # release. Use a more recent release. Note that PYENV_RELEASE might
    # misleadingly be set from the outside if we don't set it here.
    export PYENV_RELEASE="v1.2.16"
    export PYENV_ROOT="$HOME/.travis-pyenv"

    # Note(JP): based on praekeltfoundation/travis-pyenv/blob/develop/setup-pyenv.sh
    # but w/o caching. See https://github.com/jgehrcke/gipc/issues/92.
    mkdir "$PYENV_ROOT"
    #curl -fsSL --retry 10 "https://github.com/pyenv/pyenv/archive/$PYENV_RELEASE.tar.gz" \
    #    | tar -xz -C "$PYENV_ROOT" --strip-components 1

    # Use head of master again.
    git clone https://github.com/pyenv/pyenv "$PYENV_ROOT"

    export PATH="$PYENV_ROOT/bin:$PATH"

    export PYTHON_BUILD_CURL_OPTS="--retry 10 --connect-timeout 10 --max-time 60"

    pyenv install -v "$PYENV_PYTHON_VERSION"
    pyenv global "$PYENV_PYTHON_VERSION"
    pyenv versions
    git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv

    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
    command -v python
    python --version

    VENV_NAME="ve-pyenv-${PYENV_PYTHON_VERSION}"
    pyenv virtualenv "$PYENV_PYTHON_VERSION" "$VENV_NAME"
    pyenv activate "$VENV_NAME"
    command -v python
    python --version
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
pip install 'pip==19.1.1' --upgrade
pip install 'setuptools==42.0.2' --upgrade

# Install gipc dependencies from its `setup.py`.
pip install .

# Install gipc test/CI dependencies.
pip install -r requirements-tests.txt

if [[ "$GEVENT_VERSION" != "default" ]]; then
    echo "Override gevent version to $GEVENT_VERSION"
    pip install "$GEVENT_VERSION" --upgrade
fi
