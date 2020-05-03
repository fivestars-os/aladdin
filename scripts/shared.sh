#!/usr/bin/env bash
# This file is for functions that can be shared between aladdin.sh and aladdin-container.sh

set -a
set -eu -o pipefail

function _extract_from_file() {
    local key="$1"
    local config_file="$2"
    local value
    if [[ -f $config_file ]]; then
        value="$(eval "jq -r .${key} $config_file")"
        if [[ "$value" != "null" ]]; then
            echo "$value"
            return 0
        fi
    fi
}

function _extract_cluster_config_value() {
    # Try extracting config from cluster config.json, default config.json, then aladdin config.json
    local key="$1"
    local value
    value=$(_extract_from_file "$key" "$ALADDIN_CONFIG_DIR/$CLUSTER_CODE/config.json")
    if ! test -z "$value"; then
        echo "$value"
        return 0
    fi
    value=$(_extract_from_file "$key" "$ALADDIN_CONFIG_DIR/default/config.json")
    if ! test -z "$value"; then
        echo "$value"
        return 0
    fi
    value=$(_extract_from_file "$key" "$ALADDIN_CONFIG_DIR/config.json")
    if ! test -z "$value"; then
        echo "$value"
        return 0
    fi
}

function time_plus_offset() {
    local offset="$1"
    local current_time="$(date +'%s')"
    echo "$((${current_time}+offset))"
}

function which_exists(){
    for cmd in "$@" ; do
        if which $cmd &>/dev/null ; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

function clear_cache_file(){
    rm -f "$HOME/.aladdin/infra/cache.json"
}

function get_or_set_cache(){
    local cache_file="$HOME/.aladdin/infra/cache.json"
    local key="$(make_hash $1)"
    local expiration="${2:-}"
    local data="${3:-}"
    local contents

    if ! jq -r . $cache_file &> /dev/null; then
        echo "{}" > "$cache_file"
    fi
    if test -z "$expiration"; then
        # function called like `get_or_set_cache "key"`
        expiration=$(jq -r --arg key "${key}" '.[$key]["expiration"] // 0' $cache_file)
    elif test -z "$data"; then
        # function called like `get_or_set_cache "key" "expiration"`
        data=true
    fi

    if [[ "$(date +'%s')" -gt "$expiration" ]]; then
        # if the key is expired, clear the data
        contents="$(jq --arg key "${key}" '.[$key] = {}' $cache_file)"
        echo "${contents}" > $cache_file
    elif ! test -z "$data"; then
        # function called like `get_or_set_cache "key" "expiration" "some data"`
        contents="$(jq --arg key "${key}" --argjson expiration "${expiration}" --argjson data "${data}" '.[$key] = {"expiration":$expiration,"data":$data}' $cache_file)"
        echo "${contents}" > $cache_file
    else
        # function called like `get_or_set_cache "key"`, echo the existing data
        echo "$(jq -r --arg key "${key}" '.[$key]["data"] // ""' $cache_file)"
    fi
    return 0
}

function make_hash(){
    local hash_cmd="$(which_exists md5sum md5)"
    echo -n "${1}" | $hash_cmd | awk '{print $1}'
}
