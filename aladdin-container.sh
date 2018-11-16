#!/usr/bin/env bash

# set -x
set -a
set -eu -o pipefail

# Export key directory paths
ALADDIN_DIR="$(cd "$(dirname "$0")" || exit 1; pwd)"
SCRIPT_DIR="$ALADDIN_DIR/scripts"
PY_MAIN="$ALADDIN_DIR/commands/python/main.py"
ALADDIN_PLUGIN_DIR="/root/aladdin-plugins"
ALADDIN_CONFIG_DIR="/root/aladdin-config"

# Export dirs/paths that are used by plugins/commands
export ALADDIN_DIR
export SCRIPT_DIR
export ALADDIN_CONFIG_DIR
export PY_MAIN

# Test user's aws configuration
function test_aws_config() {
    echo "Testing aws configuration..."
    # See if we the current aws profile configured
    if ! aws configure list --profile "$AWS_PROFILE" &>/dev/null; then
        echo "Could not find aws profile: $AWS_PROFILE; please check your ~/.aws/config and ~/.aws/credentials files"
        exit 1
    fi
    # Do a test aws cli call for the current aws profile
    if ! aws s3 ls --profile "$AWS_PROFILE" &>/dev/null; then
        echo "Your aws $AWS_PROFILE credentials or config may be malformed; please check your ~/.aws/config and ~/.aws/credentials files"
        exit 1
    fi
    echo "aws configuration check successful!"
}

function source_cluster_env() {
    local env_file_path
    env_file_path="$ALADDIN_CONFIG_DIR/$CLUSTER_CODE/env.sh"

    # check which env it is and import appropriate environment variables
    if [ ! -f "$env_file_path" ]; then
        echo "Error: Unable to find environment file ${env_file_path} for specified cluster ${CLUSTER_CODE}"
        exit 1
    fi

    echo "Including environment variables from script ${env_file_path}"
    source "$env_file_path"
}

function exec_command_or_plugin() {
    # Exectute a container command in order python command > bash command > container plugin
    local plugin_path command_path

    python_command_path="$ALADDIN_DIR/commands/python/command/${command//-/_}.py"
    bash_command_path="$ALADDIN_DIR/commands/bash/container/$command/$command"
    plugin_path="$ALADDIN_PLUGIN_DIR/container/$command/$command"

    if [[ -f "$python_command_path" || $command == "--help" || $command == "-h" ]]; then
        exec python3 "$PY_MAIN" "$command" "$@"
    fi

    if [[ -x "$bash_command_path" ]]; then
        exec "$bash_command_path" "$@"
    fi

    if [[ -x "$plugin_path" ]]; then
        exec "$plugin_path" "$@"
    fi

    echo "Error: unknown command $command for aladdin"
}

function _replace_aws_secret() {
    local creds username password server
    creds=$(aws ecr get-login)
    username=$(echo $creds | cut -d ' ' -f4)
    password=$(echo $creds | cut -d ' ' -f6)
    server=$(echo $creds | cut -d ' ' -f9)
    kubectl delete secret aws || true
    kubectl create secret docker-registry aws --docker-username="$username" --docker-password="$password" --docker-server="$server" --docker-email="can be anything"
}

function environment_init() {
    echo "START ENVIRONMENT CONFIGURATION============================================="
    echo "CLUSTER_CODE = $CLUSTER_CODE"
    echo "NAMESPACE = $NAMESPACE"

    # Kops uses AWS_PROFILE instead of AWS_DEFAULT_PROFILE
    export AWS_PROFILE="$AWS_DEFAULT_PROFILE"

    # Sanity check the user's aws configuration if init is set
    $INIT && test_aws_config

    # Make sure we are on local or that cluster has been created before initializing helm, creating namespaces, etc
    if "$IS_LOCAL" || ( kops export kubecfg --name $CLUSTER_NAME &> /dev/null && \
        kops validate cluster --name $CLUSTER_NAME ) &> /dev/null; then

        if "$IS_LOCAL"; then
            mkdir -p $HOME/.kube/
            cp $HOME/.kube_local/config $HOME/.kube/config
            sed 's/: .*[\\\/]\([a-z]*\.[a-z]*\)$/: \/root\/.minikube\/\1/g' $HOME/.kube_local/config > $HOME/.kube/config
        else
            cp $HOME/.kube/config $HOME/.kube_local/$CLUSTER_NAME.config
        fi

        kubectl config set-context "$NAMESPACE.$CLUSTER_NAME" --cluster "$CLUSTER_NAME" --namespace="$NAMESPACE" --user "$CLUSTER_NAME"
        kubectl config use-context "$NAMESPACE.$CLUSTER_NAME"

        if $INIT; then
            kubectl create namespace --cluster $CLUSTER_NAME $NAMESPACE || true
            helm init --upgrade --wait || true
            _replace_aws_secret || true
            $PY_MAIN namespace-init --force
        fi
    fi

    echo "END ENVIRONMENT CONFIGURATION==============================================="

}

source_cluster_env
environment_init
exec_command_or_plugin "$@"
