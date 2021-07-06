#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin refresh command" {
    # Call aladdin refresh 
    $PY_MAIN refresh aladdin-test-server
    node_port=$(kubectl get svc aladdin-test-server -o json | jq -r '.spec.ports[] | select (.name == "http").nodePort')
    sleep 60
    [ $(curl "127.0.0.1:$node_port/ping") == "aladdin-test-message2" ]
}
