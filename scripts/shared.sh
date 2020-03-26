#!/usr/bin/env bash
# This file is for functions that can be shared between aladdin.sh and aladdin-container.sh

set -a
set -eu -o pipefail

function _extract_cluster_config_value() {
    # Try extracting config from cluster config.json, default config.json, then aladdin config.json
    local value
    value="$1"
    jq -nr --arg value "$value" 'first(inputs | (if .[$value] == null then empty else .[$value] end))' \
        "$ALADDIN_CONFIG_DIR/$CLUSTER_CODE/config.json" "$ALADDIN_CONFIG_DIR/default/config.json" \
        "$ALADDIN_CONFIG_DIR/config.json"
}
