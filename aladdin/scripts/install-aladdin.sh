#!/usr/bin/env bash

PYPI_INDEX_URL="https://pypi.internal.fivestars.com/simple/"

ALADDIN_VERSION=$(python3 -m pip index versions -i ${PYPI_INDEX_URL} aladdin | grep "LATEST:" | awk '{print $2}')

INSTALLED_VERSION="$(python3 -m pipx list --json 2>/dev/null | jq -r -j '.venvs.aladdin.metadata.main_package.package_version // ""') || echo -n ''"

if ! command -v pipx &> /dev/null || python3 -m pip list --outdated | grep pipx &> /dev/null
then
    python3 -m pip install --user --upgrade pipx
    python3 -m pipx ensurepath
fi

CURRENT_VERSION=$(python3 -m pipx list --json | jq -r -j '.venvs.aladdin.metadata.main_package.package_version // ""')

if [[ ! "$ALADDIN_VERSION" == "$CURRENT_VERSION" ]]; then
    python3 -m pipx install aladdin@${ALADDIN_VERSION} -i ${PYPI_INDEX_URL} --force
fi
