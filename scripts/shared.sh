#!/usr/bin/env bash
# This file is for functions that can be shared between aladdin.sh and aladdin-container.sh

set -a
set -eu -o pipefail

function _extract_cluster_config_value() {
    # Try extracting config from cluster config.json, default config.json, then aladdin config.json
    local key="$1"
    local value file

    file="$ALADDIN_CONFIG_DIR/$CLUSTER_CODE/config.json"
    if [[ -f $file ]]; then
        value="$(eval "jq -r .${key} $file")"
        if [[ $value != "null" ]]; then
            echo $value
            return 0
        fi
    fi
    file="$ALADDIN_CONFIG_DIR/default/config.json"
    if [[ -f $file ]]; then
        value="$(eval "jq -r .${key} $file")"
        if [[ $value != "null" ]]; then
            echo $value
            return 0
        fi
    fi

    file="$ALADDIN_CONFIG_DIR/config.json"
    if [[ -f $file ]]; then
        value="$(eval "jq -r .${key} $file")"
        if [[ $value != "null" ]]; then
            echo $value
            return 0
        fi
    fi
}

function _get_last_launched() {
    local last_launched_file="$HOME/.aladdin/infra/last_launch.json"
    local current_time="$(date +'%s')"
    local key="$1"
    local expiration="$2"

    if [[ ! -f "$last_launched_file" ]]; then
        echo "{}" > "$last_launched_file"
    fi
    local previous_run="$(jq -r --arg key "${key}" '.[$key] // 0' $last_launched_file)"
    if [[ "$current_time" -gt "$((${previous_run:-0}+init_every))" || "$previous_run" -gt "$current_time" ]]; then
        local contents="$(jq --arg key "${key}" --argjson value "${current_time}" '.[$key] = $value' $last_launched_file)"
        echo "${contents}" > $last_launched_file
        return 0
    fi
    return 1
}
