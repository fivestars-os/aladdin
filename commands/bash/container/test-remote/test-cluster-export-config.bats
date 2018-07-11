#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin cluster export-config command" {
    # Call cluster export-config
    "$CLUSTER_COMMAND_PATH" export-config
}
