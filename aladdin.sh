#!/usr/bin/env bash

# set -x
set -a
set -eu -o pipefail
# if user presses control-c, exit from script
function ctrl_trap(){ exit 1 ; }
trap ctrl_trap INT

# Set defaults on command line args
DEV=false
INIT=false
CLUSTER_CODE=LOCAL
NAMESPACE=default
IS_TERMINAL=true
SKIP_PROMPTS=false
KUBERNETES_VERSION="1.19.7"
MANAGE_SOFTWARE_DEPENDENCIES=true

# Set key directory paths
ALADDIN_DIR="$(cd "$(dirname "$0")" ; pwd)"
SCRIPT_DIR="$ALADDIN_DIR/scripts"
ALADDIN_PLUGIN_DIR=

ALADDIN_BIN="$HOME/.aladdin/bin"
PATH="$ALADDIN_BIN":"$PATH"

source "$SCRIPT_DIR/shared.sh" # to load _extract_cluster_config_value

function get_config_path() {
    if [[ ! -f "$HOME/.aladdin/config/config.json" ]]; then
        echo "Unable to find config directory. Please use 'aladdin config set config_dir <config path location>' to set config directory"
        exit 1
    fi
    ALADDIN_CONFIG_DIR=$(jq -r .config_dir $HOME/.aladdin/config/config.json)
    if [[ "$ALADDIN_CONFIG_DIR" == null ]]; then
        echo "Unable to find config directory. Please use 'aladdin config set config_dir <config path location>' to set config directory"
        exit 1
    fi
    ALADDIN_CONFIG_FILE="$ALADDIN_CONFIG_DIR/config.json"
}

function get_plugin_dir() {
    if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
        ALADDIN_PLUGIN_DIR=$(jq -r .plugin_dir $HOME/.aladdin/config/config.json)
        if [[ "$ALADDIN_PLUGIN_DIR" == null ]]; then
            ALADDIN_PLUGIN_DIR=
        fi
    fi
}

function get_manage_software_dependencies() {
    if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
        MANAGE_SOFTWARE_DEPENDENCIES=$(jq -r .manage.software_dependencies $HOME/.aladdin/config/config.json)
        if [[ "$MANAGE_SOFTWARE_DEPENDENCIES" == null ]]; then
            MANAGE_SOFTWARE_DEPENDENCIES=true
        fi
    fi
}
# Check for cluster name aliases and alias them accordingly
function check_cluster_alias() {
    cluster_alias=$(jq -r --arg key "$CLUSTER_CODE" '.cluster_aliases[$key]' "$ALADDIN_CONFIG_FILE")
    if [[ $cluster_alias != null ]]; then
        export CLUSTER_CODE=$cluster_alias
    fi
}

function get_config_variables() {
    # Get host directory that will be mounted onto the docker container
    if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
        HOST_DIR=$(jq -r .host_dir $HOME/.aladdin/config/config.json)
        if [[ "$HOST_DIR" == null ]]; then
            # defaults to osx
            HOST_DIR="/Users"
        fi
    fi
    # Get k3d service port
    K3D_SERVICE_PORT=8081 # default value
    if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
        K3D_SERVICE_PORT=$(jq -r .k3d.service_port $HOME/.aladdin/config/config.json)
        if [[ "$K3D_SERVICE_PORT" == null ]]; then
            K3D_SERVICE_PORT=8081
        fi
    fi
    # Get k3d api port
    K3D_API_PORT=6550 # default value
    if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
        K3D_API_PORT=$(jq -r .k3d.api_port $HOME/.aladdin/config/config.json)
        if [[ "$K3D_API_PORT" == null ]]; then
            K3D_API_PORT=6550
        fi
    fi
}

function get_host_addr() {
    case "$OSTYPE" in
        linux*) HOST_ADDR="172.17.0.1" ;;
        *)      HOST_ADDR="host.docker.internal" ;;
    esac
}

function check_and_handle_init() {
    # Check if we need to force initialization
    local last_launched_file init_every current_time previous_run
    last_launched_file="$HOME/.infra/last_checked_${NAMESPACE}_${CLUSTER_CODE}"
    init_every=3600
    current_time="$(date +'%s')"
    # create last launched file if it doesn't exit
    mkdir -p "$(dirname "$last_launched_file")" && touch "$last_launched_file"
    previous_run="$(cat "$last_launched_file")"
    if [[ "$current_time" -gt "$((${previous_run:-0}+init_every))" || "$previous_run" -gt "$current_time" ]]; then
        INIT=true
    fi
    # Handle initialization logic
    if "$INIT"; then
        if "$MANAGE_SOFTWARE_DEPENDENCIES"; then
            "$SCRIPT_DIR"/infra_k8s_check.sh --force
        fi
        check_or_start_k3d
        readonly repo_login_command="$(jq -r '.aladdin.repo_login_command' "$ALADDIN_CONFIG_FILE")"
        if [[ "$repo_login_command" != "null" ]]; then
            eval "$repo_login_command"
        fi
        local aladdin_image="$(jq -r '.aladdin.repo' "$ALADDIN_CONFIG_FILE"):$(jq -r '.aladdin.tag' "$ALADDIN_CONFIG_FILE")"
        if [[ $aladdin_image == *"/"* ]]; then
            docker pull "$aladdin_image"
        fi
        echo "$current_time" > "$last_launched_file"
    else
        if "$MANAGE_SOFTWARE_DEPENDENCIES"; then
            "$SCRIPT_DIR"/infra_k8s_check.sh
        fi
        check_or_start_k3d
    fi
}

function _start_k3d() {
    # start k3d cluster
    k3d cluster create LOCAL \
        --api-port "$K3D_API_PORT" \
        -p "$K3D_SERVICE_PORT:80@loadbalancer" \
        --image "rancher/k3s:v$KUBERNETES_VERSION-k3s1" \
        --k3s-server-arg "--tls-san=$HOST_ADDR" \
        # these last two are for compatibility with newer linux kernels
        # https://k3d.io/faq/faq/#solved-nodes-fail-to-start-or-get-stuck-in-notready-state-with-log-nf_conntrack_max-permission-denied
        # https://github.com/rancher/k3d/issues/607
        --k3s-server-arg "--kube-proxy-arg=conntrack-max-per-core=0" \
        --k3s-agent-arg "--kube-proxy-arg=conntrack-max-per-core=0"
}

function check_or_start_k3d() {
    if ! k3d cluster list | grep LOCAL > /dev/null; then
        echo "Starting k3d LOCAL cluster... (this will take a moment)"
        _start_k3d
    else
        if ! kubectl version | grep "Server" | grep "$KUBERNETES_VERSION" > /dev/null; then
            echo "k3d detected on the incorrect version, stopping and restarting"
            k3d cluster delete LOCAL > /dev/null
            check_or_start_k3d
        fi
    fi
}

function set_cluster_helper_vars() {
    IS_LOCAL="$(_extract_cluster_config_value is_local)"
    if [[ -z "$IS_LOCAL" ]]; then
        IS_LOCAL=false
    fi

    IS_PROD="$(_extract_cluster_config_value is_prod)"
    if [[ -z "$IS_PROD" ]]; then
        IS_PROD=false
    fi

    IS_TESTING="$(_extract_cluster_config_value is_testing)"
    if [[ -z "$IS_TESTING" ]]; then
        IS_TESTING=false
    fi
}

function exec_host_command() {
    local command_path

    command_path="$ALADDIN_DIR/aladdin/bash/host/$command/$command"
    if [[ -x "$command_path" ]]; then
        exec "$command_path" "$@"
    fi
}

function exec_host_plugin() {
    local plugin_path

    if [[ -n "$ALADDIN_PLUGIN_DIR" ]]; then
        plugin_path="$ALADDIN_PLUGIN_DIR/host/$command/$command"
        if [[ -x "$plugin_path" ]]; then
            exec "$plugin_path" "$@"
        fi
    fi
}

function pathnorm(){
    # Normalize the path, the path should exists
    typeset path="$1"
    echo "$(cd "$path" ; pwd)"
}

function confirm_production() {
    if $IS_TERMINAL ; then  # if this is an interactive shell and not jenkins or piped input, then verify
        echo "Script is running in a terminal. Let us make user aware that this is production";
        echo -ne '\033[;31mYou are on production. Please type "production" to continue: \033[0m'; read -r
        if [[ ! $REPLY = "production" ]]; then
            echo 'Exiting since you did not type production'
            exit 0
        fi
    else
        echo "This is production environment. This script is NOT running in a terminal, hence supressing user prompt to type 'production'";
    fi
}

function handle_ostypes() {
    case "$OSTYPE" in
        jenkins*|linux*|darwin*) # Running on jenkins/linux/osx
            true # use the default pathnorm
        ;;
        cygwin*) # Cygwin under windows
            function pathnorm(){
                # Normalize the path, the path should exists
                typeset abspath="$(cd "$1" ; pwd)"
                echo "${abspath#/cygdrive}"
            }
        ;;
        win*|bsd*|solaris*) # Windows
            echo "Not sure how to launch docker here. Exiting ..."
            return 1
        ;;
        *)
            echo "unknown OS: $OSTYPE"
            echo "Not sure how to launch docker here. Exiting ..."
            return 1
        ;;
    esac
}

function prepare_volume_mount_options() {
    # if this is not production or staging, we are mounting kubernetes folder so that
    # config maps and other settings can be customized by developers
    VOLUME_MOUNTS_OPTIONS=""
    if "$DEV"; then
        VOLUME_MOUNTS_OPTIONS="-v $(pathnorm "$ALADDIN_DIR")/aladdin:/root/aladdin/aladdin"
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -v $(pathnorm "$ALADDIN_DIR")/scripts:/root/aladdin/scripts"
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -v $(pathnorm "$ALADDIN_DIR")/aladdin-container.sh:/root/aladdin/aladdin-container.sh"
    fi

    if [[ -n "$ALADDIN_PLUGIN_DIR" ]]; then
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -v $(pathnorm $ALADDIN_PLUGIN_DIR):/root/aladdin-plugins"
    fi

    if "$DEV" || "$IS_LOCAL"; then
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -v $HOST_DIR:/aladdin_root$HOST_DIR"
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -w /aladdin_root$(pathnorm "$PWD")"
    fi
}

function prepare_ssh_options() {
    local ssh_src

    if $(jq -r '.ssh.agent // false' $HOME/.aladdin/config/config.json ); then
        # Give the container access to the agent socket and tell it where to find it
        if [[ -z ${SSH_AUTH_SOCK:-} ]]; then
            echo >&2 "Aladdin is configured to use the host's ssh agent (ssh.agent == true) but SSH_AUTH_SOCK is empty."
            exit 1
        fi
        SSH_OPTIONS="-e SSH_AUTH_SOCK=${SSH_AUTH_SOCK} -v ${SSH_AUTH_SOCK}:${SSH_AUTH_SOCK}"
    else
        # Default behavior is to attempt to mount the host's .ssh directory into root's home.
        case "$OSTYPE" in
            cygwin*) ssh_src="/.ssh" ;;
            *)       ssh_src="$(pathnorm ~/.ssh)" ;;
        esac
        SSH_OPTIONS="-v ${ssh_src}:/root/.ssh"
    fi
}

function enter_docker_container() {
    if "$IS_PROD" && ! "$SKIP_PROMPTS"; then
        confirm_production
    fi

    FLAGS="--privileged --rm -i"
    # Set pseudo-tty only if aladdin is being run from a terminal
    if $IS_TERMINAL ; then
        FLAGS+="t"
    fi

    local aladdin_image="${IMAGE:-"$(jq -r '.aladdin.repo' "$ALADDIN_CONFIG_FILE"):$(jq -r '.aladdin.tag' "$ALADDIN_CONFIG_FILE")"}"

    docker run $FLAGS \
        `# Environment` \
        -e "DEV=$DEV" \
        -e "INIT=$INIT" \
        -e "CLUSTER_CODE=$CLUSTER_CODE" \
        -e "NAMESPACE=$NAMESPACE" \
        -e "IS_LOCAL=$IS_LOCAL" \
        -e "IS_PROD=$IS_PROD" \
        -e "IS_TESTING=$IS_TESTING" \
        -e "SKIP_PROMPTS=$SKIP_PROMPTS" \
        -e "K3D_API_PORT=$K3D_API_PORT" \
        -e "HOST_ADDR=$HOST_ADDR" \
        -e "command=$command" \
        `# Mount host credentials` \
        `# Mount destination for aws creds will not be /root/.aws because we will possibly make` \
        `# changes there that we don't want propagated on the host's ~/.aws` \
        -v "$(pathnorm ~/.aws):/root/tmp/.aws" \
        -v "$(pathnorm ~/.kube):/root/.kube_local" \
        -v "$(pathnorm ~/.aladdin):/root/.aladdin" \
        -v "$(pathnorm $ALADDIN_CONFIG_DIR):/root/aladdin-config" \
        -v /var/run/docker.sock:/var/run/docker.sock \
        ${VOLUME_MOUNTS_OPTIONS} \
        ${SSH_OPTIONS} \
        "$aladdin_image" \
        `# Finally, launch the command` \
        /root/aladdin/aladdin-container.sh "$@"
}

command="-h" # default command is help
while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--cluster)
            CLUSTER_CODE="$2"
            shift # past argument
        ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift # past argument
        ;;
        --image)
            IMAGE="$2"
            shift # past argument
        ;;
        -i|--init)
            INIT=true
        ;;
        --dev)
            DEV=true
        ;;
        --non-terminal)
            IS_TERMINAL=false
        ;;
        --skip-prompts)
            SKIP_PROMPTS=true
        ;;
        *)
            command="$1"
            shift
            break
        ;;
    esac
    shift # past argument or value
done

exec_host_command "$@"
get_config_path
get_plugin_dir
get_host_addr
get_manage_software_dependencies
exec_host_plugin "$@"
check_cluster_alias
get_config_variables
check_and_handle_init
set_cluster_helper_vars
handle_ostypes
prepare_volume_mount_options
prepare_ssh_options
enter_docker_container "$@"
