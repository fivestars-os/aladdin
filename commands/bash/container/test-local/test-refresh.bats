#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin refresh command" {
    # Call aladdin refresh
    $PY_MAIN refresh aladdin-test-server
    node_port=$(kubectl get svc aladdin-test-server -o json | jq -r '.spec.ports[] | select (.name == "http").nodePort')
    local minikube_ip=$(kubectl config view -o jsonpath='{.clusters[?(@.name == "minikube")].cluster.server}' | sed 's/.....$//')
    sleep 60
    [ $(curl "$minikube_ip:$node_port/ping") == "aladdin-test-message2" ]
}
