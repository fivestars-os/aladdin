#!/usr/bin/env bash
set -eu -o pipefail
#set -x

# This script install the dependencies for infrastructure for windows and mac
# The minimum dependency for windows is cygwin with wget.
# No minimum dependency found for mac

# To force the script to do the full check, use the parameter '--force'

#- from : https://github.com/rancher/k3d/releases
VERSION_K3D="4.4.4"
#- from : https://github.com/kubernetes/kubernetes/releases
VERSION_KUBECTL="1.19.7"
#- from : https://github.com/kubernetes/helm/releases
VERSION_HELM="3.5.2"


# This script is meant to check and test the necessary tools for using the infra tools.
#
# To run k3d :
# - k3d
# - kubectl
# - helm

# To launch the bash script
# - jq
# - aws cli
# - git

# COLORS variables
FG_GREEN="$(tput setaf 2 2>/dev/null || printf "\e[32m")"
FG_YELLOW="$(tput setaf 3 2>/dev/null || printf "\e[33m")"
FG_RED="$(tput setaf 1 2>/dev/null || printf "\e[31m")"
BOLD="$(tput bold 2>/dev/null || printf "\e[1m")"
FG_YELLOW_BOLD="$FG_YELLOW$BOLD"
FG_RED_BOLD="$FG_RED$BOLD"
RESET_COLOR="$(tput sgr0 2>/dev/null || printf "\e[0m")"

############################
# Check things are installed
############################
# Do not show the check again if it has already been installed
ALREADY_INSTALLED_FILE="$HOME/.infra/installed"

ALADDIN_BIN="$HOME/.aladdin/bin"


function which_exists(){
    for cmd in "$@" ; do
        if which $cmd &>/dev/null ; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}



hash_cmd="$(which_exists md5sum md5)"
SCRIPT_HASH="$("$hash_cmd" < "$0" | xargs)"

if [[ ! -f "$ALREADY_INSTALLED_FILE" ]] ;then
    mkdir -p "$(dirname "$ALREADY_INSTALLED_FILE")"
    touch "$ALREADY_INSTALLED_FILE"
fi

EXISTING_CONTENT="$(cat "$ALREADY_INSTALLED_FILE")"

NEED_INSTALL=false
if [[ "X$EXISTING_CONTENT" != "X$SCRIPT_HASH" ]] ;then
    NEED_INSTALL=true
fi

if [[ "${1:-}" == "--force" ]] ;then
    NEED_INSTALL=true
fi


# Where we are
DIR_PATH="$(cd "$(dirname $0)" ; pwd)"
FILES_DIR="$DIR_PATH/infra_k8s_check_files"


platform=""
bin_path=""
install_cmd=""
case "$OSTYPE" in
    cygwin)
        platform=win
        # On windows, the equivalent would be /cygdrive/c/Windows/System32, but this need admin access
        # So we are using the cygwin path
        bin_path="/usr/local/bin"
        install_cmd="apt-cyg install"
        ;;
    darwin*)
        platform=mac
        bin_path="/usr/local/bin"
        install_cmd="brew install"
        ;;
    linux-musl) #alpine linux
        platform=alpine
        bin_path="/usr/local/bin"
        install_cmd="apk add -y"
        ;;
    linux-gnu)  #ubuntu
        platform=ubuntu
        bin_path="/usr/local/bin"
        install_cmd="apt-get install -y"
        ;;
    jenkins*)
      platform=jenkins
      bin_path="$HOME"
      echo $bin_path
      install_cmd="apt-get install -y"
      ;;
    *) echo "Operating system not supported" >&2 ; exit 1 ;;
esac

# We could do that
#bin_path="$(echo "$PATH" | cut -d: -f1)"

##################
# Output functions
##################
function check_start(){ printf "check $1 ... " ; }
function check_ok(){ printf "${FG_GREEN}OK${RESET_COLOR}\n"; }
function check_installing(){ printf "installing ... " ; }
function check_done(){ printf "${FG_GREEN}done${RESET_COLOR}\n"; }
function check_error(){ printf "${FG_RED_BOLD}FAILED%s${RESET_COLOR}\n" "${1:-}"; exit 1 ; }
function check_warn() { printf "${FG_YELLOW_BOLD}Please install %s${RESET_COLOR}\n" "$1"; return 1 ; }

##################
# Check functions (returning "true" or "false")
##################

function find_bin_path(){ # Command name
    # Try to get smart about the path
    typeset command="$1"
    typeset default_bin_path="/usr/local/bin"
    if ! has_prog "$command" ; then
        echo "$default_bin_path/$command"
        return 0
    fi
    typeset current_bin_path="$(dirname "$(which "$command")")"
    typeset num_default="$(echo "$PATH" | tr ':' '\n' | grep -n "$default_bin_path" | head -1 | cut -d: -f1)"
    typeset num_current="$(echo "$PATH" | tr ':' '\n' | grep -n "$current_bin_path" | head -1 | cut -d: -f1)"

    # If we don't find anything
    if [[ -z "$num_default" ]]; then
        echo "$current_bin_path/$command"
        return 0
    fi

    if [[ "$num_default" -lt "$num_current" ]]; then
        echo "$default_bin_path/$command"
        return 0
    else
        echo "$current_bin_path/$command"
        return 0
    fi
}

function has_prog(){ hash -r ; which $1 >/dev/null 2>/dev/null ; }
function version(){ { eval "$1" 2>/dev/null || true ; } | grep -E "$2" >/dev/null 2>/dev/null ; }

# We use this function to check and install things we can install in ~/.aladdin/bin
function check_and_install(){
    typeset msg="$1" install_name="$2"
    typeset check_fct="check_${install_name}"
    typeset install_fct="install_${install_name}_${platform}"

    check_start "$msg"
    if eval "$check_fct" ; then
        check_ok
    else
        check_installing
        if ! eval "$install_fct" ; then
            check_error
            exit 1
        fi

        if ! eval "$check_fct" ; then
            check_error " Installation failed"
        fi

        check_done
    fi
}

# We use this to check for things that can only be installed on the system, and then prompt the user
# to install it if it is missing
function check_and_warn() {
    typeset msg="$1" install_name="$2"
    typeset check_fct="check_${install_name}"

    check_start "$msg"
    if eval "$check_fct" ; then
        check_ok
    else
        check_warn "$install_name"
    fi
}

# Entry/exit tmp directory, instead of using the /tmp, use the Download
function tmp_dir(){
    case "$platform" in
        win) typeset res="$(cygpath "$USERPROFILE")/Downloads/infra_tmp" ;;
        *) typeset res="${HOME}/Downloads/infra_tmp" ;; # mac alpine ubuntu
    esac

    rm -rf "$res"
    mkdir -p "$res"
    echo "$res"
}

function clean_tmp_dir(){ tmp_dir ; }


function WGET(){
    typeset url="$1" file_dest="$2"

    if ! wget --help &>/dev/null && which powershell.exe &>/dev/null ; then
        # Wget might not be there, using powershell instead
        powershell.exe -Command Invoke-WebRequest -OutFile "$(cygpath -w "$file_dest")" "$url"
        return 0
    fi

    wget --output-document="$file_dest" --quiet "$url"
}

function install_url_tgz(){
    typeset name="$1" file_path="$2" url="$3"
    typeset tmp_dir="$(tmp_dir)"
    typeset tmp_file="$tmp_dir/$name.tgz"
    WGET "$url" "$tmp_file"
    ( cd "$tmp_dir" ; tar -xvf "$tmp_file" ; )
    #find "$tmp_dir"
    install "${tmp_dir}/$file_path" "$ALADDIN_BIN" ; clean_tmp_dir
}

function install_url_zip(){
    typeset name="$1" file_path="$2" url="$3"
    typeset tmp_dir="$(tmp_dir)"
    typeset tmp_file="$tmp_dir/$name.zip"
    WGET "$url" "$tmp_file"
    ( cd "$tmp_dir" ; unzip "$name.zip" -d "$name.zip.dir" &>/dev/null )
    install "${tmp_file}.dir/$file_path" "$ALADDIN_BIN" ; clean_tmp_dir
}

function install_url_exe(){
    typeset name="$1" url="$2"
    typeset tmp_file="$(tmp_dir)/$name"
    WGET "$url" "$tmp_file"
    #find "$(dirname "$tmp_file")"
    install "$tmp_file" "$ALADDIN_BIN" ; clean_tmp_dir
}

function install_url_cmd(){
    typeset name="$1" url="$2"
    typeset tmp_file="$(tmp_dir)/$name"
    WGET "$url" "$tmp_file"
    install "$tmp_file" "$ALADDIN_BIN" ; clean_tmp_dir
}

##################
# Installing functions
##################

function check_aptcyg(){ has_prog apt-cyg ; }
function install_aptcyg_win(){
    typeset tmp_file="$(tmp_dir)/apt-cyg"
    # Wget might not be there, using powershell instead
    powershell.exe -Command Invoke-WebRequest -OutFile "$(cygpath -w "$tmp_file")" \
        http://rawgit.com/transcode-open/apt-cyg/master/apt-cyg

    install "$tmp_file" "$(find_bin_path apt-cyg)"
    clean_tmp_dir
}


function check_unzip(){ has_prog unzip ; }
function install_unzip_win(){ apt-cyg install unzip ; }


function check_brew(){ has_prog brew ; }
function install_brew_mac(){
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
}

function check_wget(){ has_prog wget ; }
function install_wget_win(){ eval $install_cmd wget >/dev/null 2>/dev/null ; }
function install_wget_mac(){ eval $install_cmd wget >/dev/null 2>/dev/null ; }
function install_wget_ubuntu(){ eval $install_cmd wget >/dev/null 2>/dev/null ; }


function check_k3d(){ version "$ALADDIN_BIN/k3d version" "$VERSION_K3D" ;}

function install_k3d() {
    curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | K3D_INSTALL_DIR=$ALADDIN_BIN TAG=v${VERSION_K3D} USE_SUDO=false bash
}

function install_k3d_win(){
    install_k3d
}
function install_k3d_mac(){
    install_k3d
}
function install_k3d_alpine(){
    install_k3d
}
function install_k3d_ubuntu(){
    install_k3d
}

function check_kubectl(){ version "$ALADDIN_BIN/kubectl version --client" "Client.*v$VERSION_KUBECTL" ; }
function install_kubectl_win(){
    typeset url="https://dl.k8s.io/v${VERSION_KUBECTL}/kubernetes-client-windows-amd64.tar.gz"
    install_url_tgz "kubectl.exe" "kubernetes/client/bin/kubectl.exe" "$url"
}
function install_kubectl_mac(){
    typeset url="https://dl.k8s.io/v${VERSION_KUBECTL}/kubernetes-client-darwin-amd64.tar.gz"
    install_url_tgz "kubectl" "kubernetes/client/bin/kubectl" "$url"
}
function install_kubectl_alpine(){
    typeset url="https://dl.k8s.io/v${VERSION_KUBECTL}/kubernetes-client-linux-amd64.tar.gz"
    install_url_tgz "kubectl" "kubernetes/client/bin/kubectl" "$url"
}
function install_kubectl_ubuntu(){
    typeset url="https://dl.k8s.io/v${VERSION_KUBECTL}/kubernetes-client-linux-amd64.tar.gz"
    install_url_tgz "kubectl" "kubernetes/client/bin/kubectl" "$url"
}


function check_helm(){ version "$ALADDIN_BIN/helm version" "$VERSION_HELM" ; }
function install_helm_win(){
    typeset url="https://get.helm.sh/helm-v${VERSION_HELM}-windows-amd64.zip"
    install_url_zip "helm.exe" "windows-amd64/helm.exe" "$url"
}
function install_helm_mac(){
    typeset url="https://get.helm.sh/helm-v${VERSION_HELM}-darwin-amd64.tar.gz"
    install_url_tgz "helm" "darwin-amd64/helm" "$url"
}
function install_helm_alpine(){
    typeset url="https://get.helm.sh/helm-v${VERSION_HELM}-linux-amd64.tar.gz"
    install_url_tgz "helm" "linux-amd64/helm" "$url"
}
function install_helm_ubuntu(){
    typeset url="https://get.helm.sh/helm-v${VERSION_HELM}-linux-amd64.tar.gz"
    install_url_tgz "helm" "linux-amd64/helm" "$url"
}

function install_jq_win(){ eval $install_cmd jq >/dev/null 2>/dev/null ; }
function install_jq_mac(){ eval $install_cmd jq >/dev/null 2>/dev/null ; }
function install_jq_alpine(){ eval $install_cmd jq >/dev/null 2>/dev/null ; }
function install_jq_ubuntu(){ eval $install_cmd jq >/dev/null 2>/dev/null ; }
function check_jq(){ has_prog jq ; }

function install_git_win(){ eval $install_cmd git >/dev/null 2>/dev/null ; }
function install_git_mac(){ eval $install_cmd git >/dev/null 2>/dev/null ; }
function install_git_alpine(){ eval $install_cmd git >/dev/null 2>/dev/null ; }
function install_git_ubuntu(){ eval $install_cmd git >/dev/null 2>/dev/null ; }
function check_git(){ has_prog git ; }

function install_python3_win(){ eval $install_cmd python3 >/dev/null 2>/dev/null ; }
function install_python3_mac(){ eval $install_cmd python3 >/dev/null 2>/dev/null ; }
function install_python3_alpine(){ eval $install_cmd python3 >/dev/null 2>/dev/null ; }
function install_python3_ubuntu(){ eval $install_cmd python3 >/dev/null 2>/dev/null ; }
function check_python3(){ has_prog python3 ; }

function install_awscli_win(){ python3 -m pip install --upgrade awscli >/dev/null 2>/dev/null ; }
function install_awscli_mac(){ python3 -m pip install --upgrade awscli >/dev/null 2>/dev/null ; }
function install_awscli_alpine(){ python3 -m pip install --upgrade awscli >/dev/null 2>/dev/null ; }
function install_awscli_ubuntu(){ pip install --upgrade awscli >/dev/null 2>/dev/null ; }
function check_awscli(){ has_prog aws ; }

function check_openssl(){ openssl version; }
function install_openssl_alpine(){ eval $install_cmd ca-certificates && update-ca-certificates && eval $install_cmd ca-certificates openssl; }
function install_openssl_ubuntu(){ eval $install_cmd ca-certificates && update-ca-certificates && eval $install_cmd ca-certificates openssl; }

function install_jq_alpine(){ eval $install_cmd jq ; }
function install_jq_ubuntu(){ eval $install_cmd jq ; }

function install_pip_ubuntu(){ eval $install_cmd python-pip ; }

function check_pip(){ has_prog pip; }
function check_socat(){ has_prog socat ; }

function main(){
    if $NEED_INSTALL ; then

      mkdir -p "$ALADDIN_BIN"

      echo "platform is $platform"
        # Launch the checks
        case "$platform" in
            win)
                check_and_warn "apt-cyg            " aptcyg
                check_and_warn "unzip              " unzip
                check_and_warn "wget               " wget
                check_and_install "k3d ($VERSION_K3D)   " k3d
                check_and_install "kubectl ($VERSION_KUBECTL)    " kubectl
                check_and_install "helm ($VERSION_HELM)       " helm
                check_and_warn "jq                 " jq
                #check_and_warn "git                " git
                check_and_warn "python3            " python3
                check_and_warn "aws-cli            " awscli

                # Only validate the script install at the end
                echo "$SCRIPT_HASH" > "$ALREADY_INSTALLED_FILE"
            ;;

            mac)
              check_and_warn "brew               " brew
              check_and_warn "wget               " wget
              check_and_install "k3d ($VERSION_K3D)        " k3d
              check_and_install "kubectl ($VERSION_KUBECTL)   " kubectl
              check_and_install "helm ($VERSION_HELM)       " helm
              check_and_warn "jq                 " jq
              #check_and_warn "git                " git
              check_and_warn "python3            " python3
              check_and_warn "aws-cli            " awscli

              # Only validate the script install at the end
              echo "$SCRIPT_HASH" > "$ALREADY_INSTALLED_FILE"
            ;;
            alpine)
              check_and_warn "openssl               " openssl
              check_and_warn "wget                " wget
              check_and_install "k3d ($VERSION_K3D)  " k3d
              check_and_install "kubectl ($VERSION_KUBECTL)    " kubectl
              check_and_install "helm ($VERSION_HELM)       " helm
              check_and_warn "jq                 " jq
              #check_and_warn "git                " git
              check_and_warn "python3            " python3
              check_and_warn "aws-cli            " awscli

              # Only validate the script install at the end
              echo "$SCRIPT_HASH" > "$ALREADY_INSTALLED_FILE"

            ;;
            ubuntu)
              #check_and_install "openssl               " openssl
              check_and_warn "wget                " wget
              check_and_install "k3d ($VERSION_K3D)  " k3d
              check_and_install "kubectl ($VERSION_KUBECTL)    " kubectl
              check_and_install "helm ($VERSION_HELM)       " helm
              check_and_warn "jq                 " jq
              #check_and_warn "git                " git
              check_and_warn "python-pip         " pip
              check_and_warn "python3            " python3
              check_and_warn "aws-cli            " awscli

              # Only validate the script install at the end
              echo "$SCRIPT_HASH" > "$ALREADY_INSTALLED_FILE"

            ;;
            jenkins)
              # for jenkins slaves, make sure that docker and aws cli is preinstalled
              # we do not need anything else

              # Only validate the script install at the end
              echo "$SCRIPT_HASH" > "$ALREADY_INSTALLED_FILE"
            ;;
        esac
    fi

}


main
