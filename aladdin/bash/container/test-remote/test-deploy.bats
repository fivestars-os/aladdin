#!/usr/bin/env bats
set -o pipefail

load test_helper

@test "Test aladdin deploy command" {
    # Call deploy
    $PY_MAIN deploy aladdin-test v1.0.0 --set-override-values affinity=
    # Check helm release is present
    helm list | grep "aladdin-test-default\s"
    # Check kubernetes resources are present
    kubectl get deploy | grep "aladdin-test-server\s"
    kubectl get deploy | grep "aladdin-test-commands\s"
    kubectl get service | grep "aladdin-test-server\s"
    kubectl get cm | grep "aladdin-test\s"
    kubectl get cm | grep "aladdin-test-nginx\s"
    kubectl get cm | grep "aladdin-test-uwsgi\s"
    kubectl get hpa | grep "aladdin-test-hpa\s"
    # Let elb become ready by sleeping for a minute
    sleep 60
    # Sync the dns after this in case it wasn't immediately ready
    $PY_MAIN sync-dns
    # Verify sync-dns by checking if cname value equals service elb
    service_elb=$(get_elb aladdin-test-server)
    [[ $service_elb == $(get_cname_value aladdin-test-server "default.$DNS_ZONE") ]]
    # Curl the service elb to make sure it matches
    wait_condition "curl $service_elb" 300
    sleep 60
    [[ $(curl "$service_elb/ping") == "aladdin-test-message" ]]
}

@test "Test aladdin deploy command with new hash" {
    # Call deploy
    $PY_MAIN deploy aladdin-test v1.0.1 --set-override-values affinity=
    # Check helm release is present
    helm list | grep "aladdin-test-default\s"
    # Check kubernetes resources are present
    kubectl get deploy | grep "aladdin-test-server\s"
    kubectl get deploy | grep "aladdin-test-commands\s"
    kubectl get service | grep "aladdin-test-server\s"
    kubectl get cm | grep "aladdin-test\s"
    kubectl get cm | grep "aladdin-test-nginx\s"
    kubectl get cm | grep "aladdin-test-uwsgi\s"
    kubectl get hpa | grep "aladdin-test-hpa\s"
    sleep 60
    [[ $(curl $(get_elb aladdin-test-server)/ping) == "aladdin-test-message2" ]]
}
