#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin build command" {
    # Call build
    $PY_MAIN build
    # Check aladdin test images are present
    docker images | grep "aladdin-test\s" | grep local
    docker images | grep "aladdin-test-commands\s" | grep local
}
