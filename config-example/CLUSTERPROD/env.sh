#!/bin/bash
export CLOUD=aws
export KUBERNETES_VERSION=v1.8.6

export MASTER_SIZE=t2.large
export MASTER_COUNT=3
export MASTER_ZONES=us-east-1a,us-east-1c,us-east-1e

export NODE_SIZE=r4.2xlarge
export NODE_COUNT=3
# to find valid availability zones, use following command
# aws ec2 describe-availability-zones
export ZONES=us-east-1a,us-east-1c,us-east-1d,us-east-1e

export DNS_ZONE=clusterprod.example.com
export CLUSTER_NAME=$DNS_ZONE
export KOPS_STATE_STORE=s3://$DNS_ZONE

export VPC=
export NETWORK_CIDR=

export AWS_DEFAULT_REGION=us-east-1
export AWS_DEFAULT_PROFILE=

export AUTHORIZATION=AlwaysAllow
export CLOUD_LABELS=
export ADMIN_ACCESS=

export IMAGE=kope.io/k8s-1.8-debian-jessie-amd64-hvm-ebs-2018-03-11
