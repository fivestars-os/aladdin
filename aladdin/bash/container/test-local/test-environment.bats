#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin environment command" {
    # Call aladdin start 
    $PY_MAIN environment aladdin-test set --args MESSAGE=aladdin-test-message2
    [[ $(kubectl describe cm | grep -A 2 MESSAGE | grep aladdin-test-message2) == "aladdin-test-message2" ]]
}
