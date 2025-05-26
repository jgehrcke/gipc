#!/bin/bash
set -o errexit
set -o errtrace
set -o pipefail
set -o xtrace

# Install newer pip and setuptools (newer than bundles with certain Python
# releases and newer than what Travis brings) -- but still pin the versions so
# that there are no moving dependencies.
pip install 'pip==25.1.1' --upgrade
pip install 'setuptools==75.3.0' --upgrade

pip install .

# Install gipc test/CI dependencies.
pip install -r requirements-tests.txt

if [[ "$GEVENT_VERSION" != "default" ]]; then
    echo "Override gevent version to $GEVENT_VERSION"
    pip install "$GEVENT_VERSION" --upgrade
fi
