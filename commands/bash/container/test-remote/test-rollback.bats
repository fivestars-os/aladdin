#!/usr/bin/env bats
set -o pipefail

load test_helper

@test "Test aladdin rollback command" {
    # Call rollback
    $PY_MAIN rollback aladdin-test
    sleep 60
    [[ $(curl $(get_elb aladdin-test-server)/ping) == "aladdin-test-message" ]]
}
