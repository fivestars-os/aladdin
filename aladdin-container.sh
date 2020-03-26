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

source "$SCRIPT_DIR/shared.sh" # to load _extract_cluster_config_value

# Test user's aws configuration
function _test_aws_config() {
    # Test aws configuration for a given profile: $1
    echo "Testing aws configuration..."
    local profile=$1
    # See if we the current aws profile configured
    if ! aws configure list --profile "$profile" >/dev/null; then
        echo "Could not find aws profile: $profile; please check your ~/.aws/config and ~/.aws/credentials files"
        exit 1
    fi
    # Do a test aws cli call for the current aws profile
    if ! aws sts get-caller-identity --profile "$profile" >/dev/null; then
        echo "Your aws $profile credentials or config may be malformed; please check your ~/.aws/config and ~/.aws/credentials files"
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
    # Execute a container command in order python command > bash command > container plugin
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

    _handle_aws_config

    # Make sure we are on local or that cluster has been created before initializing helm, creating namespaces, etc
    if "$IS_LOCAL" || ( kops export kubecfg --name $CLUSTER_NAME > /dev/null && \
        kops validate cluster --name $CLUSTER_NAME ) > /dev/null; then

        if "$IS_LOCAL"; then
            mkdir -p $HOME/.kube/
            cp $HOME/.kube_local/config $HOME/.kube/config
            sed 's/: .*[\\\/]\([a-z]*\.[a-z]*\)$/: \/root\/.minikube\/\1/g' $HOME/.kube_local/config > $HOME/.kube/config
        else
            cp $HOME/.kube/config $HOME/.kube_local/$CLUSTER_NAME.config
        fi

        kubectl config set-context "$NAMESPACE.$CLUSTER_NAME" --cluster "$CLUSTER_NAME" --namespace="$NAMESPACE" --user "$CLUSTER_NAME"
        kubectl config use-context "$NAMESPACE.$CLUSTER_NAME"

        _handle_authentication_config

        if $INIT; then
            kubectl create namespace --cluster $CLUSTER_NAME $NAMESPACE || true
            _initialize_helm
            _replace_aws_secret || true
            $PY_MAIN namespace-init --force
        fi
    fi

    echo "END ENVIRONMENT CONFIGURATION==============================================="

}

function _initialize_helm() {
    local rbac_enabled="$(_extract_cluster_config_value rbac_enabled)"
    if $rbac_enabled; then
        kubectl -n kube-system create serviceaccount tiller || true
        kubectl create clusterrolebinding tiller --clusterrole cluster-admin --serviceaccount=kube-system:tiller || true
        helm init --service-account=tiller --upgrade --wait || true
    else
        helm init --upgrade --wait || true
    fi
}

function _handle_authentication_config() {
    # This function adds appropriate users to kubeconfig, and exports necessary AUTHENTICATION variables
    # export AUTHENTICATION_ENABLED for change-permissions and bash command
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
      apiVersion: client.authentication.k8s.io/v1alpha1
      args:
      - token
      - -i
      - $CLUSTER_NAME
      - -r
      - $role_arn
      command: aws-iam-authenticator
EOT
}

function _handle_aws_config() {
    # This function does quite a few things with aws credentials/config files:
    # 1) Move the mounted aws creds to ~/.aws
    # 2) Checks if we have the BASTION_ACCOUNT_ENABLED configuration from our aladdin-config
    # 3) If we do:
    #        - export appropriate BASTION_ variables for other aladdin commands
    #        - sanity test our aws configuration for the bastion account if INIT and not IS_LOCAL
    #        - appropriately update our credentials/config files with the desired possible roles
    #            - here we are calling the add-aws-assume-role-config aladdin command
    # 4) If we do not:
    #        - sanity test our aws configuration for the cluster's current aws account if INIT and not IS_LOCAL
    # 5) Export AWS_PROFILE=$AWS_DEFAULT_PROFILE because kops uses the former

    # Move aws credentials away from mount so we don't edit the host's aws files
    cp -r /root/tmp/.aws /root/.aws
    # See if bastion account is enabled
    export BASTION_ACCOUNT_ENABLED="$(_extract_cluster_config_value bastion_account_enabled)"
    if "$BASTION_ACCOUNT_ENABLED"; then
        # Export BASTION_ACCOUNT_PROFILE, needed by add-aws-assume-role-config command
        export BASTION_ACCOUNT_PROFILE="$(_extract_cluster_config_value bastion_account_profile)"
        # Need to unset AWS_DEFAULT_PROFILE because aws requires that entry to exist even if we
        # are specifying --profile to a separate present entry, which is expected in the bastion case
        local aws_default_profile_temp="$AWS_DEFAULT_PROFILE"
        unset AWS_DEFAULT_PROFILE
        # Test aws config for bastion account
        "$INIT" && _test_aws_config "$BASTION_ACCOUNT_PROFILE"
        # Alias the add assume role config command
        add_assume_role_config="$ALADDIN_DIR/commands/bash/container/add-aws-assume-role-config/add-aws-assume-role-config"
        # Need to add aws configuration based on publish configuration.
        # We need to do this because the publish ECR may be a different aws account than the one
        # your cluster is provisioned in
        publish_config="$(_extract_cluster_config_value publish)"
        publish_profile="$(jq -r '.aws_profile' <<< $publish_config)"
        publish_role="$(jq -r '.aws_role_to_assume' <<< $publish_config)"
        publish_mfa_enabled="$(jq -r '.aws_role_mfa_required' <<< $publish_config)"
        "$add_assume_role_config" "$publish_role" "$publish_profile" "$publish_mfa_enabled" 3600 # 1 hour
        # Need to add aws configuration for current cluster's aws account
        aws_profile="$(_extract_cluster_config_value bastion_account_profile_to_assume)"
        aws_role="$(_extract_cluster_config_value bastion_account_role_to_assume)"
        aws_mfa_enabled="$(_extract_cluster_config_value bastion_account_mfa_enabled)"
        "$add_assume_role_config" "$aws_role" "$aws_profile" "$aws_mfa_enabled" 3600 # 1 hour
        # We reset AWS_DEFAULT_PROFILE here because that entry will be present in aws config files now
        export AWS_DEFAULT_PROFILE="$aws_default_profile_temp"
    else
        # Test aws config for current cluster's aws account if INIT and not IS_LOCAL
        if "$INIT" && ! "$IS_LOCAL"; then
            _test_aws_config "$AWS_DEFAULT_PROFILE"
        fi
    fi
    # Kops uses AWS_PROFILE instead of AWS_DEFAULT_PROFILE
    export AWS_PROFILE="$AWS_DEFAULT_PROFILE"
}

source_cluster_env
environment_init
exec_command_or_plugin "$@"
