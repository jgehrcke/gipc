#!/bin/bash
echo "Running gipc unit tests..."
cd test
py.test
cd ..
echo -e "\n\nRunning setup.py check & readme2html..."
python setup.py check
python setup.py --long-description | rst2html.py > /dev/null
echo -e "\n\nRunning PEP8 check..."
pep8
echo -e "\n\nRunning pylint..."
cd gipc
pylint --reports=n --include-ids=y --disable=C0103,W0212,W0511,W0142,R0903 gipc.py
cd ..
