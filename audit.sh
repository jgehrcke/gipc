#!/bin/bash
echo ">>> Run gipc unit tests, investigate code coverage ..."
cd test && py.test --cov-report term --cov-report html --cov gipc
cd ..
echo -e "\n>>> Run setup.py check..."
python setup.py check
echo -e "\n>>> Run python setup.py --long-description | rst2html.py > /dev/null ..."
python setup.py --long-description | rst2html.py > /dev/null
echo -e "\n>>> Run rst2html.py CHANGELOG.rst > /dev/null ..."
rst2html.py CHANGELOG.rst > /dev/null
echo -e "\n>>> Run PEP8 check ..."
pep8
echo -e "\n>>> Run pylint on gipc/gipc.py ..."
pylint --reports=n --disable=C0103,W0212,W0511,W0142,R0903 gipc/gipc.py
