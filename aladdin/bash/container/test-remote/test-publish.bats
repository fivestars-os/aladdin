#!/usr/bin/env bats
set -o pipefail

function setup_file {
    aws s3 rm --recursive "s3://$S3_HELM_CHART_BUCKET/helm_charts/0.0.0/aladdin-test" || true
    aws ecr delete-repository --repository-name aladdin-test-commands --force || true
    aws ecr delete-repository --repository-name aladdin-test --force || true
}

function setup {
    if [ "$BATS_TEST_NUMBER" -eq 1 ]; then
        setup_file
    fi
}

@test "Test aladdin publish command" {
    # Call build
    $PY_MAIN publish --repo aladdin-test --git-ref v1.0.0
    # Check aladdin test images are present
    aws s3 ls "s3://$S3_HELM_CHART_BUCKET/helm_charts/0.0.0/" | grep aladdin-test
    [[ 1 == $(aws ecr list-images --repository-name aladdin-test | jq '.imageIds | length') ]]
    [[ 1 == $(aws ecr list-images --repository-name aladdin-test-commands | jq '.imageIds | length') ]]
    # Publish this as well for deploy testing
    $PY_MAIN publish --repo aladdin-test --git-ref v1.0.1
}
