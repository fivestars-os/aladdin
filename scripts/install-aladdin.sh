#!/usr/bin/env bash

ALADDIN_VERSION=${ALADDIN_VERSION:-$(\
curl -s https://api.github.com/repos/fivestars-os/aladdin/releases/latest | \
jq -r -j '.tag_name' || \
echo -n "master")}

INSTALLED_VERSION="$(python3 -m pipx list --json 2>/dev/null | jq -r -j '.venvs.aladdin.metadata.main_package.package_version // ""') || echo -n ''"

if [[ "$ALADDIN_VERSION" == "1.19.7.37" ]] && [[ "$INSTALLED_VERSION" == "1.19.7.36" ]]; then
    python3 -m pipx uninstall aladdin
    python3 -m pip uninstall pipx -y
fi

if ! command -v pipx &> /dev/null || python3 -m pip list --outdated | grep pipx &> /dev/null
then
    python3 -m pip install --user --upgrade pipx
    python3 -m pipx ensurepath
fi

CURRENT_VERSION=$(python3 -m pipx list --json | jq -r -j '.venvs.aladdin.metadata.main_package.package_version // ""')

if [[ ! "$ALADDIN_VERSION" == "$CURRENT_VERSION" ]]; then
    python3 -m pipx install git+https://github.com/fivestars-os/aladdin.git@${ALADDIN_VERSION} --force
fi
