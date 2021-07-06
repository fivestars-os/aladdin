#!/bin/bash
# for local env, very few settings are needed, this file intentionally blank
export CLOUD=
export KUBERNETES_VERSION=v1.9.0

export MASTER_SIZE=
export MASTER_COUNT=
export MASTER_ZONES=

export NODE_SIZE=
export NODE_COUNT=
# to find valid availability zones, use following command
# aws ec2 describe-availability-zones
export ZONES=

export DNS_ZONE=LOCAL
export CLUSTER_NAME=$DNS_ZONE
export KOPS_STATE_STORE=s3://$DNS_ZONE

export VPC=
export NETWORK_CIDR=

export AWS_DEFAULT_REGION=us-east-1
export AWS_DEFAULT_PROFILE=abcdfgh
