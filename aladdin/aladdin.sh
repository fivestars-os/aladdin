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
SKIP_PROMPTS=false
KUBERNETES_VERSION="1.27.13"

# Set key directory paths
ALADDIN_DIR="$(cd "$(dirname "$0")" ; pwd)"
SCRIPT_DIR="$ALADDIN_DIR/scripts"

ALADDIN_BIN="$HOME/.aladdin/bin"
PATH="$ALADDIN_BIN":"$PATH"

source "$SCRIPT_DIR/shared.sh"

function get_host_addr() {
    case "$OSTYPE" in
        linux*) HOST_ADDR="172.17.0.1" ;;
        *)      HOST_ADDR="host.docker.internal" ;;
    esac
}

function check_and_handle_init() {
    # Check if we need to force initialization
    local last_launched_file init_every current_time previous_run
    last_launched_file="$HOME/.aladdin/infra_k8s_check_${NAMESPACE}_${CLUSTER_CODE}"
    # once per day
    init_every=$((3600 * 24))
    current_time="$(date +'%s')"
    # create last launched file if it doesn't exit
    mkdir -p "$(dirname "$last_launched_file")" && touch "$last_launched_file"
    previous_run="$(cat "$last_launched_file")"
    if [[ "$current_time" -gt "$((${previous_run:-0}+init_every))" || "$previous_run" -gt "$current_time" ]]; then
        INIT=true
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
    if ! docker image inspect $ALADDIN_IMAGE &> /dev/null; then
        readonly repo_login_command="$(jq -r '.aladdin.repo_login_command' "$ALADDIN_CONFIG_DIR/config.json")"
        if [[ "$repo_login_command" != "null" ]]; then
            eval "$repo_login_command"
        fi
        docker pull "$ALADDIN_IMAGE"
    fi
}

function exec_host_command() {
    local command_path

    command_path="$ALADDIN_DIR/bash/host/$command/$command"
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
    echoerr "Script is running in a terminal. Let us make user aware that this is production";
    >&2 echo -ne '\033[;31mYou are on production. Please type "production" to continue: \033[0m'; read -r
    if [[ ! $REPLY = "production" ]]; then
        echoerr 'Exiting since you did not type production'
        exit 0
    fi
}

function prepare_volume_mount_options() {
    # if this is not production or staging, we are mounting kubernetes folder so that
    # config maps and other settings can be customized by developers
    VOLUME_MOUNTS_OPTIONS=""
    if [ "$ALADDIN_DEV" = true ]; then
        VOLUME_MOUNTS_OPTIONS="-v $(pathnorm "$ALADDIN_DIR"):/root/aladdin/aladdin"
    fi

    if [[ -n "$ALADDIN_PLUGIN_DIR" ]]; then
        VOLUME_MOUNTS_OPTIONS="$VOLUME_MOUNTS_OPTIONS -v $(pathnorm $ALADDIN_PLUGIN_DIR):/root/aladdin-plugins"
    fi

    if [ "$ALADDIN_DEV" = true ] || [ "$IS_LOCAL" = true ]; then
        if [[ -f "$HOME/.aladdin/config/config.json" ]]; then
            HOST_DIR=$(jq -r .host_dir $HOME/.aladdin/config/config.json)
            if [[ "$HOST_DIR" == "None" ]]; then
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

    FLAGS="--privileged --rm -it"

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
        /root/aladdin/aladdin/aladdin-container.sh "$@"
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

get_host_addr
exec_host_command "$@"
exec_host_plugin "$@"
check_and_handle_init
prepare_volume_mount_options
prepare_ssh_options
enter_docker_container "$@"
