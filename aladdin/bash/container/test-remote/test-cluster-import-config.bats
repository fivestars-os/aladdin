#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin cluster import-config command" {
    # Call cluster import-config
    "$CLUSTER_COMMAND_PATH" import-config
}
