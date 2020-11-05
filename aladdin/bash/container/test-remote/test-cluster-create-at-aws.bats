#!/usr/bin/env bats
set -o pipefail

load test_helper

@test "Test aladdin cluster create-at-aws command" {
    # Call cluster create-at-aws
    "$CLUSTER_COMMAND_PATH" create-at-aws
    wait_condition "kops validate cluster" 1200
    # sleep more for cluster to fully warmup? getting errors on looking up api.<cluster zone> without this
    sleep 600
    # Initialize environment so it can be interacted with (this should be reworked later)
    INIT=true environment_init
}
