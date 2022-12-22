#!/usr/bin/env bash
# This file is for functions that can be shared between aladdin.sh and aladdin-container.sh

set -a
set -eu -o pipefail

function _extract_cluster_config_value() {
    # Try extracting config from cluster config.json, default config.json, then aladdin config.json
    local path default value
    path="$1"
    default="${2:-}"
    if [[ -z "${ALADDIN_CONFIG_DIR:-}" ]]; then
        return 0
    fi
    value=$(jq -nr "first(inputs | (if .$path == null then empty else .$path end))" \
        "$ALADDIN_CONFIG_DIR/$CLUSTER_CODE/config.json" "$ALADDIN_CONFIG_DIR/default/config.json" \
        "$ALADDIN_CONFIG_DIR/config.json")

    if [[ -z "$value" ]]; then
        echo "$default"
    else
        echo "$value"
    fi
}


function echoerr() { cat <<< "$@" 1>&2; }
