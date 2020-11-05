#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin undeploy command" {
    # Call undeploy
    $PY_MAIN undeploy aladdin-test
    sleep 60
    run bash -c "helm list | grep aladdin-test-default"
    [ "$status" = 1 ]
    run bash -c "kubectl get deploy | grep 'aladdin-test-server\s'"
    [ "$status" = 1 ]
    run bash -c "kubectl get deploy | grep 'aladdin-test-redis\s'"
    [ "$status" = 1 ]
    run bash -c "kubectl get deploy | grep 'aladdin-test-commands\s'"
    [ "$status" = 1 ]
    run bash -c "kubectl get service | grep 'aladdin-test-server\s'"
    [ "$status" = 1 ]
    run bash -c "kubectl get service | grep 'aladdin-test-redis\s'"
    [ "$status" = 1 ]
    run bash -c "kubectl get cm | grep 'aladdin-test\s'"
    [ "$status" = 1 ]
    run bash -c "kubectl get cm | grep 'aladdin-test-nginx\s'"
    [ "$status" = 1 ]
    run bash -c "kubectl get cm | grep 'aladdin-test-uwsgi\s'"
    [ "$status" = 1 ]
    run bash -c "kubectl get hpa | grep 'aladdin-test-hpa\s'"
    [ "$status" = 1 ]
}
