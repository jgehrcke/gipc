#!/bin/bash
echo "Running gipc unit tests, investigate code coverage..."
py.test --cov gipc test
if [ -d coverage_html ]; then
    rm -rf coverage_html/*
fi
coverage html -d coverage_html
echo -e "\n\nRunning setup.py check & readme2html..."
python setup.py check
python setup.py --long-description | rst2html.py > /dev/null
rst2html.py CHANGELOG.rst > /dev/null
echo -e "\n\nRunning PEP8 check..."
pep8
echo -e "\n\nRunning pylint..."
pylint --reports=n --include-ids=y --disable=C0103,W0212,W0511,W0142,R0903 gipc/gipc.py
