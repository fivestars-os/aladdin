#!/usr/bin/env bash

ALADDIN_VERSION=${ALADDIN_VERSION:-$(\
curl -s https://api.github.com/repos/fivestars-os/aladdin/releases/latest | \
python3 -c 'import json,sys;print(json.load(sys.stdin)["tag_name"])' || \
echo -n "master")}

python3 -m pip install --user --upgrade pipx
python3 -m pipx ensurepath
python3 -m pipx install git+https://github.com/fivestars-os/aladdin.git@${ALADDIN_VERSION} --force
