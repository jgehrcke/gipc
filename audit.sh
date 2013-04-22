#!/bin/bash
echo ">>> Running gipc unit tests, investigate code coverage..."
cd test && py.test --cov gipc
if [ $? -eq 0 ]; then
    if [ -d coverage_html ]; then
        rm -rf coverage_html/*
    fi
    coverage html -d coverage_html
    cd ..
fi
echo -e "\n>>> Running setup.py check..."
python setup.py check
echo -e "\n>>> Running python setup.py --long-description | rst2html.py > /dev/null..."
python setup.py --long-description | rst2html.py > /dev/null
echo -e "\n>>> Running rst2html.py CHANGELOG.rst > /dev/null..."
rst2html.py CHANGELOG.rst > /dev/null
echo -e "\n>>> Running PEP8 check..."
pep8
echo -e "\n>>> Running pylint..."
pylint --reports=n --include-ids=y --disable=C0103,W0212,W0511,W0142,R0903 gipc/gipc.py
