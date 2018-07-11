#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin cluster create-config command" {
    # Call cluster create-config
    "$CLUSTER_COMMAND_PATH" create-config
    # Check cluster ktest is present
    kops get cluster | grep "$DNS_ZONE\s"
}
