#!/usr/bin/env bash

# set -x
set -a
set -eu -o pipefail

# Export key directory paths
ALADDIN_DIR="$(cd "$(dirname "$0")" || exit 1; pwd)"
SCRIPT_DIR="$ALADDIN_DIR/scripts"
PY_MAIN="aladdin"
ALADDIN_PLUGIN_DIR="/root/aladdin-plugins"
ALADDIN_CONFIG_DIR="/root/aladdin-config"

# Export dirs/paths that are used by plugins/commands
export ALADDIN_DIR
export SCRIPT_DIR
export ALADDIN_CONFIG_DIR
export PY_MAIN

source "$SCRIPT_DIR/shared.sh"

function source_cluster_env() {
    local env_file_path
    env_file_path="$ALADDIN_CONFIG_DIR/$CLUSTER_CODE/env.sh"

    # check which env it is and import appropriate environment variables
    if [ ! -f "$env_file_path" ]; then
        echoerr "Error: Unable to find environment file ${env_file_path} for specified cluster ${CLUSTER_CODE}"
        exit 1
    fi

    echoerr "Including environment variables from script ${env_file_path}"
    source "$env_file_path"
}

function exec_command_or_plugin() {
    # Execute a container command in order python command > bash command > container plugin
    local plugin_path command_path

    python_command_path="$ALADDIN_DIR/aladdin/commands/${command//-/_}.py"
    bash_command_path="$ALADDIN_DIR/aladdin/bash/container/$command/$command"
    plugin_path="$ALADDIN_PLUGIN_DIR/container/$command/$command"

    if [[ -f "$python_command_path" || $command == "--help" || $command == "-h" ]]; then
        exec "$PY_MAIN" "$command" "$@"
    fi

    if [[ -x "$bash_command_path" ]]; then
        exec "$bash_command_path" "$@"
    fi

    if [[ -x "$plugin_path" ]]; then
        exec "$plugin_path" "$@"
    fi

    echoerr "Error: unknown command $command for aladdin"
}

function environment_init() {
    echoerr "START ENVIRONMENT CONFIGURATION============================================="
    echoerr "CLUSTER_CODE = $CLUSTER_CODE"
    echoerr "NAMESPACE = $NAMESPACE"

    # export AUTHENTICATION_ENABLED for change-permissions and bash command. By default it is false.
    # It will only get set to true if the cluster is ready and it is enabled in aladdin-config
    export AUTHENTICATION_ENABLED=false

    # If we're doing ssh-agent forwarding add a dummy ssh config
    if [ ! -f $HOME/.ssh/config ] && [ ! -z "${SSH_AUTH_SOCK:-}" ]
    then
        mkdir -p $HOME/.ssh/
        git config --global url.ssh://git@github.com/.insteadOf https://github.com/
        echo -e "Host github.com\n\tStrictHostKeyChecking no\n\tForwardAgent yes\n" > $HOME/.ssh/config
    fi

    if "$IS_LOCAL"; then
        local cluster_provider="k3d"
        if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
            cluster_provider=$(jq -r '.local_cluster_provider // "k3d"' $HOME/.aladdin/config/config.json)
        fi
        if [[ "$cluster_provider" == "rancher-desktop" ]]; then
            mkdir -p $HOME/.kube/
            sed 's/127.0.0.1/172.17.0.1/g' $HOME/.kube_local/config > $HOME/.kube/config
            kubectl config set-context "rancher-desktop" --cluster "rancher-desktop" --namespace="$NAMESPACE" --user "rancher-desktop"
            kubectl config use-context "rancher-desktop"
        fi
        if [[ "$cluster_provider" == "k3d" ]]; then
            K3D_SERVICE_PORT=8081 # default value
            if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
                K3D_SERVICE_PORT=$(jq -r '.k3d.service_port // 8081' $HOME/.aladdin/config/config.json)
            fi
            # Get k3d api port
            K3D_API_PORT=6550 # default value
            if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
                K3D_API_PORT=$(jq -r '.k3d.api_port // 6550' $HOME/.aladdin/config/config.json)
            fi
            mkdir -p $HOME/.kube/
            sed "s;https://0.0.0.0:$K3D_API_PORT;https://$HOST_ADDR:$K3D_API_PORT;g" $HOME/.kube_local/config > $HOME/.kube/config
            kubectl config set-context "$NAMESPACE.k3d-$CLUSTER_NAME" --cluster "k3d-$CLUSTER_NAME" --namespace="$NAMESPACE" --user "admin@k3d-$CLUSTER_NAME"
            kubectl config use-context "$NAMESPACE.k3d-$CLUSTER_NAME"
        fi
    else
        _get_kubeconfig
    fi

    _handle_authentication_config
    kubectl cluster-info

    if $INIT; then
        $ALADDIN_DIR/aladdin/bash/container/create-namespace/create-namespace $NAMESPACE || true
        $PY_MAIN namespace-init --force
    fi

    echoerr "END ENVIRONMENT CONFIGURATION==============================================="

}

function _get_kubeconfig() {
    local cluster_operator=$(_extract_cluster_config_value "cluster_operator" "kops")

    # Allow using a different aws profile from aladdin config
    _AWS_PROFILE="$(_extract_cluster_config_value ${cluster_operator}.aws_profile $AWS_PROFILE)"

    if [[ "$cluster_operator" == "kops" ]]; then
        # if using SSO, AWS_SDK_LOAD_CONFIG needs to be true
        AWS_SDK_LOAD_CONFIG=true AWS_PROFILE=$_AWS_PROFILE kops export kubecfg --name $CLUSTER_NAME --admin
    fi
    if [[ "$cluster_operator" == "eks" ]]; then
        # if using SSO, AWS_SDK_LOAD_CONFIG needs to be true
        AWS_PROFILE=$_AWS_PROFILE aws eks update-kubeconfig \
            --region $AWS_REGION \
            --name $CLUSTER_NAME
    fi

    # keep a copy of the original kubeconfig
    cp $HOME/.kube/config $HOME/.kube_local/$CLUSTER_NAME.config

    if [[ "$cluster_operator" == "kops" ]]; then
        kubectl config set-context "$NAMESPACE.$CLUSTER_NAME" --cluster "$CLUSTER_NAME" --namespace="$NAMESPACE" --user "$CLUSTER_NAME"
        kubectl config use-context "$NAMESPACE.$CLUSTER_NAME"
    fi
}

function _handle_authentication_config() {
    # This function adds appropriate users to kubeconfig, and exports necessary AUTHENTICATION variables
    export AUTHENTICATION_ENABLED="$(_extract_cluster_config_value authentication_enabled)"
    if $AUTHENTICATION_ENABLED; then
        AUTHENTICATION_ROLES="$(_extract_cluster_config_value authentication_roles)"
        AUTHENTICATION_ALADDIN_ROLE="$(_extract_cluster_config_value authentication_aladdin_role)"
        # export AUTHENTICATION_DEFAULT_ROLE for bash command
        export AUTHENTICATION_DEFAULT_ROLE="$(_extract_cluster_config_value authentication_default_role)"
        # export AUTHENTICATION_ALLOWED_CHANGE_ROLES for change-permissions command
        export AUTHENTICATION_ALLOWED_CHANGE_ROLES="$(_extract_cluster_config_value authentication_allowed_change_roles)"
        jq -r '.|keys[]' <<< "$AUTHENTICATION_ROLES" | while read name ; do
            role_arn="$(jq -r --arg name "$name" '.[$name]' <<< $AUTHENTICATION_ROLES)"
            _add_authentication_user_to_kubeconfig "$name" "$role_arn"
        done
        kubectl config set-context "$NAMESPACE.$CLUSTER_NAME" --cluster "$CLUSTER_NAME" --namespace="$NAMESPACE" --user "$AUTHENTICATION_ALADDIN_ROLE"
    fi
}

function _add_authentication_user_to_kubeconfig() {
    name="$1"
    role_arn="$2"
    cat <<EOT >> $HOME/.kube/config
- name: $name
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      args:
      - token
      - -i
      - $CLUSTER_NAME
      - -r
      - $role_arn
      command: aws-iam-authenticator
EOT
}

source_cluster_env
environment_init
exec_command_or_plugin "$@"
