#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin cluster delete command" {
    # Call cluster import-config
    "$CLUSTER_COMMAND_PATH" delete
    run bash -c 'kops get cluster | grep "$DNS_ZONE"\s'
    [ "$status" = 1 ]
}
