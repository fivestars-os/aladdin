#!/usr/bin/env bash

# Bash init script for aladdin.
# Provide shortcuts functions for a lot of features

function change_to_aladdin_permission() {
    echo "Temporarily changing your permissions to run aladdin command..."
    kubectl config set-context "$NAMESPACE.$CLUSTER_NAME" --cluster "$CLUSTER_NAME" \
        --namespace="$NAMESPACE" --user "$AUTHENTICATION_ALADDIN_ROLE" > /dev/null
}

function get_current_user() {
    kubectl config get-contexts | grep $(kubectl config current-context) | awk '{print $4}'
}

function restore_permission() {
    local old_user
    old_user="$1"
    echo "Reverting your permissions back to $old_user"
    kubectl config set-context "$NAMESPACE.$CLUSTER_NAME" --cluster "$CLUSTER_NAME" \
        --namespace="$NAMESPACE" --user "$old_user" > /dev/null
}

function with_aladdin_perms_wrapper() {
    if "$AUTHENTICATION_ENABLED"; then
        old_user="$(get_current_user)"
        change_to_aladdin_permission
    fi
    "$@"
    if "$AUTHENTICATION_ENABLED"; then
        restore_permission "$old_user"
    fi
}

# Allow aladdin python commands to be accessible directly
for cmd_path in `ls $ALADDIN_DIR/aladdin/python/command/*.py`; do
    cmd=$(basename ${cmd_path%%.*});
    cmd=${cmd//_/-}
    alias $cmd="with_aladdin_perms_wrapper $PY_MAIN $cmd"
done

for cmd in `ls $ALADDIN_DIR/aladdin/bash/container/`; do
    if [[ "$cmd" == "change-permissions" ]]; then
        alias $cmd="$ALADDIN_DIR/aladdin/bash/container/$cmd/$cmd"
    else
        alias $cmd="with_aladdin_perms_wrapper $ALADDIN_DIR/aladdin/bash/container/$cmd/$cmd"
    fi
done

alias help="$PY_MAIN -h"
