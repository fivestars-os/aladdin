#!/usr/bin/env bash

# Bash init script for aladdin.
# Provide shortcuts functions for a lot of features

echo "This bash contain a lot helpful function aliases to aladdin commands."
echo "See scripts/bash_cmd_includes.bash in aladdin for details."

source "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/bash_cmd_includes.bash"

# Add some shell command completions
source /etc/profile.d/bash_completion.sh
source <(kubectl completion bash)
source <(helm completion bash)
complete -C "$(which aws_completer)" aws
