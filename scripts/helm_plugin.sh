#!/usr/bin/env bash

set -a
set -eu -o pipefail

aladdin helm-values $4
