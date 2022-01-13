#!/bin/bash
set -o errexit
set -o errtrace
set -o pipefail
set -o xtrace

# Install newer pip and setuptools (newer than bundles with certain Python
# releases and newer than what Travis brings) -- but still pin the versions so
# that there are no moving dependencies.
pip install 'pip==21.3.1' --upgrade
pip install 'setuptools==59.6.0' --upgrade

# Install gipc dependencies from its `setup.py`. Also: "DEPRECATION: A future
# pip version will change local packages to be built in-place without first
# copying to a temporary directory. We recommend you use
# --use-feature=in-tree-build to test your packages with this new behavior
# before it becomes the default"
pip install --use-feature=in-tree-build .

# Install gipc test/CI dependencies.
pip install -r requirements-tests.txt

if [[ "$GEVENT_VERSION" != "default" ]]; then
    echo "Override gevent version to $GEVENT_VERSION"
    pip install "$GEVENT_VERSION" --upgrade
fi
