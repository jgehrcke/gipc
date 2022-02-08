#!/usr/bin/env bash

# Note: run this from the root directory of the repository, as in `bash
# ci/release.sh` This is not actually doing a release, but runs most of the
# requires steps and performs or documents most of the final testing. Comments
# at the bottom indicate further steps to be run manually.

set -o errexit
set -o errtrace
set -o nounset
set -o pipefail

# Set this before running this script.
echo $EXPECTED_VERSION_NUMBER

# Require to be on master branch.
git rev-parse --abbrev-ref HEAD | grep master || echo "not on master branch"

echo "Running ci/audit.sh"
# Expect this to run (among others)
#  python setup.py sdist
#  twine check dist/*
chronic bash ci/audit.sh # chronic is in moreutils

EXPECTED_DIST_PATH="dist/gipc-${EXPECTED_VERSION_NUMBER}.tar.gz"

if [ -f "${EXPECTED_DIST_PATH}" ]; then
    echo "${EXPECTED_DIST_PATH}" found
else
    echo "${EXPECTED_DIST_PATH} not found"
    exit 1
fi

# Do not error out if upload fails (allow for repeated execution)
twine upload --repository-url https://test.pypi.org/legacy/ "${EXPECTED_DIST_PATH}" || true

set -x
# Use `--no-dependencies` because even after installing gevent from regular PyPI,
# the installation of gipc from TestPyPi then cannot resolve its dependencies
# because gevent is not on TestPyPi.
docker run -it --rm -v $(pwd)/examples:/gipc_examples python:3.8-slim-buster /bin/bash -c \
"
    pip install gevent && \
    pip install --index-url https://test.pypi.org/simple/ gipc==${EXPECTED_VERSION_NUMBER} --upgrade --no-dependencies && \
    python -c 'import gipc; print(gipc.__file__); print(gipc.__version__)' && \
    python /gipc_examples/gipc_benchmark.py
"

echo "Test release looks good, might want to actually release"

# upload to the actual PyPI
# again, make sure to be on master/release branch.
# review current checkout, review last commit

#   git status
#   git diff
#   git log
#   git checkout master && git pull
#   git rev-parse --abbrev-ref HEAD
#
#   Did anything change? One more commit pushed?
#   Re-run this entire script! Also delete
#   last test release from PyPI, and make sure
#   the one corresponding to the actual commit
#   is uploaded. Review
#   https://test.pypi.org/manage/project/gipc/releases/
#
#   twine upload dist/gipc-xxx.tar.gz
#
#   git tag -a 1.1.1 -m 'Release 1.1.1'
#   git push --tags


# take local docs build and upload to
# sftp ...... gehrcke.de/home/<snip>/gipc_docs_website/20xx-xx-xx/
# Test that at https://gehrcke.de/gipc/20xx-xx-xx/
# move/link things if it looks good

# write email to gevent mailing list, tweet, blog : )
