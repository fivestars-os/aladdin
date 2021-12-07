#!/usr/bin/env bash

ALADDIN_VERSION=${ALADDIN_VERSION:-$(\
curl -s https://api.github.com/repos/fivestars-os/aladdin/releases/latest | \
python3 -c 'import json,sys;print(json.load(sys.stdin)["tag_name"])' || \
echo -n "master")}

if ! command -v pipx &> /dev/null
then
    python3 -m pip install --user --upgrade pipx
    python3 -m pipx ensurepath
fi

CURRENT_VERSION=$(pipx list --json | jq -r .venvs.aladdin.metadata.main_package.package_version)

if [[ ! "$ALADDIN_VERSION" == "$CURRENT_VERSION" ]]; then
    python3 -m pipx install git+https://github.com/fivestars-os/aladdin.git@${ALADDIN_VERSION} --force
    exit 1
fi
