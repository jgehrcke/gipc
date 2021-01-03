#!/bin/bash
set -ex

# Set script directory to be the current working directory.
cd "$(dirname "$0")"

python gipc_benchmark.py
python raw_largemsg_bench.py
python synchronization.py
python serverclient.py
python wsgimultiprocessing.py

# Send SIGINT after 5 seconds. If the process does
# not terminate in response to that send SIGKILL
# after 7 seconds. When SIGINT terminates the
# program then `timeout` will return with the
# exit status of the program. When `timeout` has
# to SIGKILL the program then it will exit
# non-zero in any case.
alias timeout=gtimeout # macos: brew install coreutils
timeout --preserve-status \
    --signal=INT \
    --kill-after=7 \
    5 python infinite_send_to_child.py
