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
    local default="${2:-}"
    local value=""
    local -a configs=(
        "$ALADDIN_CONFIG_DIR/$CLUSTER_CODE/config.json"
        "$ALADDIN_CONFIG_DIR/default/config.json"
        "$ALADDIN_CONFIG_DIR/config.json"
    )
    for config in "${configs[@]}"; do
        value=$(jq -r ".$key" "$config")
        if [[ "$value" != "null" ]]; then
            echo "$value"
            return 0
        fi
    done
    if test -n "$default"; then
        echo "$default"
    fi
}

function _time_plus_offset() {
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

function set_cache() {
    local cache_file="$HOME/.aladdin/infra/cache.json"
    local key="$(make_hash $1)"
    local data=${2:-}
    local expiration="$(_time_plus_offset ${3:-3600})"
    contents="$(jq --arg key "${key}" --argjson expiration "${expiration}" --argjson data "${data}" '.[$key] = {"expiration":$expiration,"data":$data}' $cache_file)"
    echo "${contents}" > $cache_file
}

function get_cached() {
    local cache_file="$HOME/.aladdin/infra/cache.json"
    local key="$(make_hash $1)"
    if ! jq -r . $cache_file &> /dev/null; then
        echo "{}" > "$cache_file"
    fi
    expiration=$(jq -r --arg key "${key}" '.[$key]["expiration"] // 0' $cache_file)
    if [[ "$(date +'%s')" -gt "$expiration" ]]; then
        return 1
    fi
    echo "$(jq -r --arg key "${key}" '.[$key]["data"] // ""' $cache_file)"
}

function set_ttl() {
    set_cache "$1" true ${2:3600}
}

function check_ttl() {
    test -n "$(get_cached "$1")"
    return $?
}

function make_hash(){
    local hash_cmd="$(which_exists md5sum md5)"
    echo -n "${1}" | $hash_cmd | awk '{print $1}'
}
