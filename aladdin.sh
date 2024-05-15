#!/usr/bin/env bash

# set -x
set -a
set -eu -o pipefail
# if user presses control-c, exit from script
function ctrl_trap(){ exit 1 ; }
trap ctrl_trap INT

# Set defaults on command line args
ALADDIN_DEV=${ALADDIN_DEV:-false}
INIT=false
CLUSTER_CODE=${CLUSTER_CODE:-LOCAL}
NAMESPACE=${NAMESPACE:-default}
IS_TERMINAL=true
SKIP_PROMPTS=false
KUBERNETES_VERSION="1.27.13"

# Set key directory paths
ALADDIN_DIR="$(cd "$(dirname "$0")" ; pwd)"
SCRIPT_DIR="$ALADDIN_DIR/scripts"

ALADDIN_BIN="$HOME/.aladdin/bin"
PATH="$ALADDIN_BIN":"$PATH"

source "$SCRIPT_DIR/shared.sh"

# Check for cluster name aliases and alias them accordingly
function check_cluster_alias() {
    if [[ -z "${ALADDIN_CONFIG_DIR:-}" ]]; then
        return 0
    fi
    cluster_alias=$(jq -r --arg key "$CLUSTER_CODE" '.cluster_aliases[$key]' "$ALADDIN_CONFIG_DIR/config.json")
    if [[ $cluster_alias != null ]]; then
        export CLUSTER_CODE=$cluster_alias
    fi
}

function get_config_variables() {
    LOCAL_CLUSTER_PROVIDER="k3d"
    if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
        LOCAL_CLUSTER_PROVIDER=$(jq -r '.local_cluster_provider // "k3d"' $HOME/.aladdin/config/config.json)
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
    # once per day
    init_every=$((3600 * 24))
    current_time="$(date +'%s')"
    # create last launched file if it doesn't exit
    mkdir -p "$(dirname "$last_launched_file")" && touch "$last_launched_file"
    previous_run="$(cat "$last_launched_file")"
    if [[ "$current_time" -gt "$((${previous_run:-0}+init_every))" || "$previous_run" -gt "$current_time" ]]; then
        INIT=true
    fi
    if ! docker image inspect $ALADDIN_IMAGE &> /dev/null; then
        readonly repo_login_command="$(jq -r '.aladdin.repo_login_command' "$ALADDIN_CONFIG_DIR/config.json")"
        if [[ "$repo_login_command" != "null" ]]; then
            eval "$repo_login_command"
        fi
        docker pull "$ALADDIN_IMAGE"
    fi
    # Handle initialization logic
    local infra_k8s_check_args=""
    if "$INIT"; then
        infra_k8s_check_args="--force"
        echo "$current_time" > "$last_launched_file"
    fi
    if "$ALADDIN_MANAGE_SOFTWARE_DEPENDENCIES"; then
        "$SCRIPT_DIR"/infra_k8s_check.sh $infra_k8s_check_args
    fi
    if "$IS_LOCAL" && [[ "$LOCAL_CLUSTER_PROVIDER" == "k3d" ]]; then
        check_or_start_k3d
    fi
}

function _start_k3d() {
    # Get k3d service port
    K3D_SERVICE_PORT=8081 # default value
    if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
        K3D_SERVICE_PORT=$(jq -r '.k3d.service_port // 8081' $HOME/.aladdin/config/config.json)
    fi
    # Get k3d api port
    K3D_API_PORT=6550 # default value
    if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
        K3D_API_PORT=$(jq -r '.k3d.api_port // 6550' $HOME/.aladdin/config/config.json)
    fi
    # start k3d cluster
    k3d cluster create LOCAL \
        --api-port "$K3D_API_PORT" \
        -p "$K3D_SERVICE_PORT:80@loadbalancer" \
        --image "rancher/k3s:v$KUBERNETES_VERSION-k3s1" \
        --k3s-server-arg "--tls-san=$HOST_ADDR" \
        `# these last two are for compatibility with newer linux kernels` \
        `# https://k3d.io/faq/faq/#solved-nodes-fail-to-start-or-get-stuck-in-notready-state-with-log-nf_conntrack_max-permission-denied` \
        `# https://github.com/rancher/k3d/issues/607` \
        --k3s-server-arg "--kube-proxy-arg=conntrack-max-per-core=0" \
        --k3s-agent-arg "--kube-proxy-arg=conntrack-max-per-core=0"
}

function check_or_start_k3d() {
    if docker info | grep "Cgroup Version: 2" > /dev/null && [[ "$KUBERNETES_VERSION" == "1.19.7" ]]; then
        echoerr "ERROR: Current version of k3d is not compatible with cgroups v2"
        echoerr "ERROR: If using Docker Desktop please downgrade to v4.2.0"
    fi
    if ! k3d cluster list | grep LOCAL > /dev/null; then
        echoerr "Starting k3d LOCAL cluster... (this will take a moment)"
        _start_k3d
    else
        if ! kubectl version | grep "Server" | grep "$KUBERNETES_VERSION" > /dev/null; then
            echoerr "k3d detected on the incorrect version, stopping and restarting"
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
        echoerr "Script is running in a terminal. Let us make user aware that this is production";
        >&2 echo -ne '\033[;31mYou are on production. Please type "production" to continue: \033[0m'; read -r
        if [[ ! $REPLY = "production" ]]; then
            echoerr 'Exiting since you did not type production'
            exit 0
        fi
    else
        echoerr "This is production environment. This script is NOT running in a terminal, hence supressing user prompt to type 'production'";
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
            echoerr "Not sure how to launch docker here. Exiting ..."
            return 1
        ;;
        *)
            echoerr "unknown OS: $OSTYPE"
            echoerr "Not sure how to launch docker here. Exiting ..."
            return 1
        ;;
    esac
}

function prepare_volume_mount_options() {
    # if this is not production or staging, we are mounting kubernetes folder so that
    # config maps and other settings can be customized by developers
    VOLUME_MOUNTS_OPTIONS=""
    if "$ALADDIN_DEV"; then
        VOLUME_MOUNTS_OPTIONS="-v $(pathnorm "$ALADDIN_DIR")/aladdin:/root/aladdin/aladdin"
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -v $(pathnorm "$ALADDIN_DIR")/scripts:/root/aladdin/scripts"
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -v $(pathnorm "$ALADDIN_DIR")/aladdin-container.sh:/root/aladdin/aladdin-container.sh"
    fi

    if [[ -n "$ALADDIN_PLUGIN_DIR" ]]; then
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -v $(pathnorm $ALADDIN_PLUGIN_DIR):/root/aladdin-plugins"
    fi

    if "$ALADDIN_DEV" || "$IS_LOCAL"; then
        if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
            HOST_DIR=$(jq -r .host_dir $HOME/.aladdin/config/config.json)
            if [[ "$HOST_DIR" == null ]]; then
                # defaults to osx
                HOST_DIR="$HOME"
            fi
        fi
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -v $HOST_DIR:/aladdin_root$HOST_DIR"
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -w /aladdin_root$(pathnorm "$PWD")"
    fi
}

function prepare_ssh_options() {
    local ssh_src

    if $(jq -r '.ssh.agent // false' $HOME/.aladdin/config/config.json ); then
        # Give the container access to the agent socket and tell it where to find it
        if [[ -z ${SSH_AUTH_SOCK:-} ]]; then
            echoerr "Aladdin is configured to use the host's ssh agent (ssh.agent == true) but SSH_AUTH_SOCK is empty."
            exit 1
        fi
        if [[ "$LOCAL_CLUSTER_PROVIDER" == "rancher-desktop" ]]; then
            case "$OSTYPE" in
                darwin*) LIMA_HOME="$HOME/Library/Application Support/rancher-desktop/lima";;
                linux*)
                    LIMA_HOME="$HOME/.local/share/rancher-desktop/lima"
                    if grep -i microsoft /proc/version &> /dev/null; then
                        LIMA_HOME="$APPDATA/rancher-desktop/lima"
                    fi
                ;;
            esac

            if [[ ! -f "$LIMA_HOME/_config/override.yaml" ]]; then
                cat <<-EOT >> $LIMA_HOME/_config/override.yaml
					ssh:
					  loadDotSSHPubKeys: true
					  forwardAgent: true
				EOT
                echoerr "Rancher Desktop (Lima) overrides applied, you might need to restart for overrides to take effect"
            fi
            SSH_AGENT_SOCKET=$(rdctl shell bash -c "echo -n \$SSH_AUTH_SOCK")
            SSH_OPTIONS="-e SSH_AUTH_SOCK=${SSH_AGENT_SOCKET} -v ${SSH_AGENT_SOCKET}:${SSH_AGENT_SOCKET}"
            if [[ -z ${SSH_AGENT_SOCKET:-} ]]; then
                echoerr "Rancher Desktop (Lima) does not seem to be running an ssh agent"
                exit 1
            fi
        else
            case "$OSTYPE" in
                # docker-desktop on mac only supports this "magic" ssh-agent socket
                # https://github.com/docker/for-mac/issues/410
                darwin*) SSH_OPTIONS="-e SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock -v /run/host-services/ssh-auth.sock:/run/host-services/ssh-auth.sock" ;;
                *)       SSH_OPTIONS="-e SSH_AUTH_SOCK=${SSH_AUTH_SOCK} -v ${SSH_AUTH_SOCK}:${SSH_AUTH_SOCK}" ;;
            esac
        fi
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

    docker run $FLAGS \
        `# Environment` \
        -e "ALADDIN_DEV=$ALADDIN_DEV" \
        -e "INIT=$INIT" \
        -e "CLUSTER_CODE=$CLUSTER_CODE" \
        -e "NAMESPACE=$NAMESPACE" \
        -e "IS_LOCAL=$IS_LOCAL" \
        -e "IS_PROD=$IS_PROD" \
        -e "IS_TESTING=$IS_TESTING" \
        -e "SKIP_PROMPTS=$SKIP_PROMPTS" \
        -e "HOST_ADDR=$HOST_ADDR" \
        -e "command=$command" \
        `# Mount host credentials` \
        -v "$(pathnorm ~/.aws):/root/.aws" \
        -v "$(pathnorm ~/.kube):/root/.kube_local" \
        -v "$(pathnorm ~/.aladdin):/root/.aladdin" \
        -v "$(pathnorm $ALADDIN_CONFIG_DIR):/root/aladdin-config" \
        -v /var/run/docker.sock:/var/run/docker.sock \
        ${VOLUME_MOUNTS_OPTIONS} \
        ${SSH_OPTIONS} \
        "$ALADDIN_IMAGE" \
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
        -i|--init)
            INIT=true
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

set_cluster_helper_vars
get_host_addr
check_cluster_alias
get_config_variables
exec_host_command "$@"
exec_host_plugin "$@"
check_and_handle_init
handle_ostypes
prepare_volume_mount_options
prepare_ssh_options
enter_docker_container "$@"
