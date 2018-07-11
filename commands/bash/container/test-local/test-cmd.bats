#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin cmd command" {
	#set -x
    # Call aladdin cmd 
    $PY_MAIN cmd aladdin-test status
}
