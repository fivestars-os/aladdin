#!/usr/bin/env bash

# Bash init script for aladdin.
# Provide shortcuts functions for a lot of features

echo "This bash contain a lot helpful function aliases to aladdin commands"
echo "Don't forget to checkout scripts/bash_profile.bash in aladdin"

function change_to_aladdin_permission() {
    echo "Temporarily changing your permissions to run aladdin command..."
    kubectl config set-context "$NAMESPACE.$CLUSTER_NAME" --cluster "$CLUSTER_NAME" \
        --namespace="$NAMESPACE" --user "$AUTHENTICATION_ALADDIN_ROLE" &> /dev/null
}

function get_current_user() {
    kubectl config get-contexts | grep $(kubectl config current-context) | awk '{print $4}'
}

function restore_permission() {
    local old_user
    old_user="$1"
    echo "Reverting your permissions back to $old_user"
    kubectl config set-context "$NAMESPACE.$CLUSTER_NAME" --cluster "$CLUSTER_NAME" \
        --namespace="$NAMESPACE" --user "$old_user" &> /dev/null
}

function with_aladdin_perms_wrapper() {
    old_user="$(get_current_user)"
    if "$AUTHENTICATION_ENABLED"; then
        change_to_aladdin_permission
    fi
    "$@"
    if "$AUTHENTICATION_ENABLED"; then
        restore_permission "$old_user"
    fi
}

# Allow aladdin python commands to be accessible directly
for cmd_path in `ls $ALADDIN_DIR/commands/python/command/*.py`; do
    cmd=$(basename ${cmd_path%%.*});
    cmd=${cmd//_/-}
    alias $cmd="with_aladdin_perms_wrapper $PY_MAIN $cmd"
done

for cmd in `ls $ALADDIN_DIR/commands/bash/container/`; do
    if [[ "$cmd" == "change-permissions" ]]; then
        alias $cmd="$ALADDIN_DIR/commands/bash/container/$cmd/$cmd"
    else
        alias $cmd="with_aladdin_perms_wrapper $ALADDIN_DIR/commands/bash/container/$cmd/$cmd"
    fi
done

alias help="$PY_MAIN -h"

source /etc/profile.d/bash_completion.sh
source <(kubectl completion bash)
source <(helm completion bash)
complete -C "$(which aws_completer)" aws
