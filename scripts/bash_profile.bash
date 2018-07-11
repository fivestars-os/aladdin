#!/usr/bin/env bash

# Bash init script for aladdin.
# Provide shortcuts functions for a lot of features

echo "This bash contain a lot helpful function aliases to aladdin commands"
echo "Don't forget to checkout scripts/bash_profile.bash in aladdin"

# Allow aladdin python commands to be accessible directly
for cmd_path in `ls $ALADDIN_DIR/commands/python/command/*.py`; do
    cmd=$(basename ${cmd_path%%.*});
    cmd=${cmd//_/-}
    alias $cmd="$PY_MAIN $cmd"
done

for cmd in `ls $ALADDIN_DIR/commands/bash/container/`; do
    alias $cmd=$ALADDIN_DIR/commands/bash/container/$cmd/$cmd
done

alias help="$PY_MAIN -h"

source /etc/profile.d/bash_completion.sh
source <(kubectl completion bash)
source <(helm completion bash)
complete -C "$(which aws_completer)" aws
