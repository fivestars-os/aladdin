#!/usr/bin/env bash

# Bash init script for aladdin.
# Provide shortcuts functions for a lot of features

echo "This bash shell contain a lot helpful function aliases to aladdin commands."
echo "See scripts/bash_cmd_includes.bash in aladdin for details."

source "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/bash_cmd_includes.bash"

# Add some shell command completions
source /etc/profile.d/bash_completion.sh
source <(kubectl completion bash)
source <(helm completion bash)
complete -C "$(which aws_completer)" aws

# if we have the directory /root/aladdin-bash-profile, source all files in that directory
if  [[ -d /root/aladdin-bash-profile ]]; then
    for f in $(ls /root/aladdin-bash-profile); do source "/root/aladdin-bash-profile/$f"; done
fi
