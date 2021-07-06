#!/usr/bin/env bats
set -o pipefail

@test "Test aladdin start command" {
    # Call aladdin start 
    $PY_MAIN start
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
}

@test "Test aladdin start command" {
    # Call aladdin start
    $PY_MAIN start
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
}
