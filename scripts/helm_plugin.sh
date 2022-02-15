#!/usr/bin/env bash

set -a
set -eu -o pipefail

# this script is invoked with the following scheme:
# helm_plugin.sh certFile keyFile caFile full-URL
aladdin helm-values -n $HELM_NAMESPACE "$4" $ARGOCD_APP_REVISION
