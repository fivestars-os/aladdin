#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin restart command" {
    # Call restart command
    $PY_MAIN restart
    # Sleep so project can finish restarting
    sleep 60
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
    run bash -c "kubectl get pv | grep 'aladdin-test-nfs-volume\s'"
    [ "$status" = 1 ]
    run bash -c "kubectl get pvc | grep 'aladdin-test-nfs-volume-claim\s'"
    [ "$status" = 1 ]
}
