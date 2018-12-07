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
CLUSTER_CODE=minikube
NAMESPACE=default
IS_TERMINAL=true
SKIP_PROMPTS=false

# Set key directory paths
ALADDIN_DIR="$(cd "$(dirname "$0")" ; pwd)"
SCRIPT_DIR="$ALADDIN_DIR/scripts"
ALADDIN_PLUGIN_DIR=

ALADDIN_BIN="$HOME/.aladdin/bin"
PATH="$ALADDIN_BIN":"$PATH"

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

# Check for cluster name aliases and alias them accordingly
function check_cluster_alias() {
    cluster_alias=$(jq -r ".cluster_aliases.$CLUSTER_CODE" "$ALADDIN_CONFIG_FILE")
    if [[ $cluster_alias != null ]]; then
        export CLUSTER_CODE=$cluster_alias
    fi
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
        "$SCRIPT_DIR"/infra_k8s_check.sh --force
        enter_minikube_env
        minikube addons enable ingress &> /dev/null
        readonly repo_login_command="$(jq -r '.aladdin.repo_login_command' "$ALADDIN_CONFIG_FILE")"
        if [[ "$repo_login_command" != "null" ]]; then
            eval "$repo_login_command"
        fi
        local aladdin_image="$(jq -r '.aladdin.repo' "$ALADDIN_CONFIG_FILE"):$(jq -r '.aladdin.tag' "$ALADDIN_CONFIG_FILE")"
        docker pull "$aladdin_image"
        echo "$current_time" > "$last_launched_file"
    else
        "$SCRIPT_DIR"/infra_k8s_check.sh
        enter_minikube_env
    fi
}

# Start minikube if we need to
function check_or_start_minikube() {
    if ! minikube status | grep Running &> /dev/null; then
        echo "Starting minikube... (this will take a moment)"
        minikube start --kubernetes-version v1.11.5 --memory 4096 &> /dev/null
        # Determine if we've installed our bootlocal.sh script to replace the vboxsf mounts with nfs mounts
        if ! "$(minikube ssh -- "test -x /var/lib/boot2docker/bootlocal.sh && echo -n true || echo -n false")"; then
            echo "Installing NFS mounts from host..."
            "$SCRIPT_DIR"/install_nfs_mounts.sh
            echo "NFS mounts installed"
        fi
        echo "Minikube started"
    fi
}

function copy_ssh_to_minikube() {
    # Some systems fail when we directly mount the host's ~/.ssh directory into the aladdin container.
    # This allows us to move the ~/.ssh directory into minikube and later mount that directory (with
    # the adjusted ownernship and permissions) such that the container can leverage the user's
    # credentials for ssh operations.
    case "$OSTYPE" in
        cygwin*) # Cygwin under windows
            echo "Copying ~/.ssh into minikube"
            (
                minikube mount --ip 192.168.99.1 "$(cygpath -w ~/.ssh):/tmp/.ssh" &
                minikube ssh -- 'sudo rm -rf /.ssh && sudo cp -r /tmp/.ssh /.ssh && sudo chmod -R 600 /.ssh'
                kill $!
            ) >/dev/null
        ;;
    esac
}

function enter_minikube_env() {
    if [[ $OSTYPE = darwin* || $OSTYPE = cygwin* || $OSTYPE = linux* ]]; then
        check_or_start_minikube
        eval "$(minikube docker-env)"
    fi
}

function _extract_cluster_config_value() {
    local value
    value="$1"
    jq -r ".$value" "$ALADDIN_CONFIG_DIR/$CLUSTER_CODE/config.json"
}

function set_cluster_helper_vars() {
    IS_LOCAL="$(_extract_cluster_config_value is_local)"
    if [[ "$IS_LOCAL" == null ]]; then
        IS_LOCAL=false
    fi

    IS_PROD="$(_extract_cluster_config_value is_prod)"
    if [[ "$IS_PROD" == null ]]; then
        IS_PROD=false
    fi

    IS_TESTING="$(_extract_cluster_config_value is_testing)"
    if [[ "$IS_TESTING" == null ]]; then
        IS_TESTING=false
    fi
}

function exec_host_command() {
    local command_path

    command_path="$ALADDIN_DIR/commands/bash/host/$command/$command"
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
        echo -ne '\e[31mYou are on production. Please type "production" to continue: \033[0m'; read -r
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
                typeset path="$1"
                typeset abspath="$(cd "$path" ; pwd)"
                cygpath --mixed "$abspath" | sed 's%^C:/%/c/%g'
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

function prepare_docker_subcommands() {
    # if this is not production or staging, we are mounting kubernetes folder so that
    # config maps and other settings can be customized by developers
    if "$DEV"; then
        DEV_CMD="-v $(pathnorm "$ALADDIN_DIR"):/root/aladdin"
        DEV_CMD="$DEV_CMD -v /:/minikube_root" # mount the whole minikube system
        DEV_CMD="$DEV_CMD --workdir /minikube_root$(pathnorm "$PWD")"
    fi

    # If on minikube mount minikube credentials
    if "$IS_LOCAL"; then
        MINIKUBE_CMD="-v $(pathnorm ~/.minikube):/root/.minikube"
        MINIKUBE_CMD="$MINIKUBE_CMD -v /:/minikube_root" # mount the whole minikube system
        MINIKUBE_CMD="$MINIKUBE_CMD --workdir /minikube_root$(pathnorm "$PWD")"
    fi

    if [[ -n "$ALADDIN_PLUGIN_DIR" ]]; then
        ALADDIN_PLUGIN_CMD="-v $(pathnorm $ALADDIN_PLUGIN_DIR):/root/aladdin-plugins"
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
    local ssh_src

    case "$OSTYPE" in
        cygwin*) ssh_src="/.ssh" ;;
        *)       ssh_src="$(pathnorm ~/.ssh)" ;;
    esac

    docker run $FLAGS \
        `# Environment` \
        -e "DEV=$DEV" \
        -e "INIT=$INIT" \
        -e "CLUSTER_CODE=$CLUSTER_CODE" \
        -e "NAMESPACE=$NAMESPACE" \
        -e "MINIKUBE_IP=$(minikube ip)" \
        -e "IS_LOCAL=$IS_LOCAL" \
        -e "IS_PROD=$IS_PROD" \
        -e "IS_TESTING=$IS_TESTING" \
        -e "SKIP_PROMPTS=$SKIP_PROMPTS" \
        -e "command=$command" \
        `# Mount host credentials` \
        -v "$(pathnorm ~/.aws):/root/.aws" \
        -v "${ssh_src}:/root/.ssh" \
        -v "$(pathnorm ~/.kube):/root/.kube_local" \
        -v "$(pathnorm ~/.aladdin):/root/.aladdin" \
        -v "$(pathnorm $ALADDIN_CONFIG_DIR):/root/aladdin-config" \
        `# Mount minikube parts` \
        -v /usr/bin/docker:/usr/bin/docker \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v /usr/lib64/libdevmapper.so.1.02:/usr/lib/libdevmapper.so.1.02 \
        `#Specific command` \
        ${DEV_CMD:-} ${MINIKUBE_CMD:-} ${ALADDIN_PLUGIN_CMD:-} \
        "$aladdin_image" \
        `#Finally, launch the command` \
        /root/aladdin/aladdin-container.sh "$@"
}

command="-h"
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
exec_host_plugin "$@"
check_cluster_alias
check_and_handle_init
copy_ssh_to_minikube
set_cluster_helper_vars
handle_ostypes
prepare_docker_subcommands
enter_docker_container "$@"
