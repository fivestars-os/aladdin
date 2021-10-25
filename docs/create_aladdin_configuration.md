# Creating Aladdin Configuration
Create a new folder for your configuration files. We recommend you call it something like `aladdin-config`, and put it under source control. There is an example of this configuration in the `config-example` folder.

## Directory Structure
```
aladdin-config/
  config.json
  default/
    config.json
    values.yaml  # Optional
  LOCAL/
    config.json
    values.yaml
    env.sh
  REMOTE-CLUSTER-1/
    config.json
    env.sh
    values.yaml
  REMOTE-CLUSTER-2/
    config.json
    env.sh
    namespace-overrides/
      test/
        config.json
        values.yaml
```

## Root config.json file
The config.json file in the root of your config directory will contain non cluster-specific configuration for your aladdin installation. Here is the config.json file from the `config-example` folder:

```
{
    "aladdin": {
      "repo": "fivestarsos/aladdin",
      "tag": "1.0.0"
    },
    "cluster_aliases": {
        "DEV": "CLUSTERDEV",
        "PROD": "CLUSTERPROD"
    },
    "git": {
        "account": "fivestars-os"
    },
    "kubernetes": {
        "label": "app"
    },
    "publish": {
        "aws_profile": "abcdefgh",
        "docker_ecr_repo": "xxxxxxxxxxxx.dkr.ecr.us-east-1.amazonaws.com/",
        "s3_helm_chart_bucket": "helm-charts-xxxxxxxxxxxxxx"
    }
}
```

- Aladdin section:
  - repo: which repo to pull aladdin from. You can change this to your internal repo if you plan on creating a custom aladdin docker image and plan on pushing it there.
  - tag: which tag of the aladdin docker image to pull
  - repo_login_command: If you plan on extending aladdin, you may need to fill this in with your internal repo's login command
- Cluster Aliases section:
  - When invoking aladdin, you can pass in the `-c/--cluster` flag to specify a cluster. Here you can add aliases for that cluster option (i.e. specify `-c DEV` rather than `-c CLUSTERDEV` in this example)
- Git section
  - account: which git account to pull from. Aladdin mounts your git credentials onto the aladdin container when you call aladdin.
- Kubernetes section:
  - label: which label to use when filter kubernetes resources. Several aladdin commands use this label to specify which exact resource to modify.
- Publish section:
  - aws_profile: which aws profile to publish your docker image and helm charts to
  - docker_ecr_repo: the ecr path of your aws profile, used to push your docker images to
  - s3_helm_chart_bucket: which bucket to store your packaged helm charts to

## Cluster env.sh file
The env.sh file in each of your subdirectories in your config folder will contain cluster-specific variables that aladdin sources. These variables are mainly used to create your cluster and to get the correct configuration. Here is the example env.sh file from the CLUSTERDEV folder.
```bash
#!/bin/bash
export CLOUD=aws
export KUBERNETES_VERSION=v1.8.6

export MASTER_SIZE=t2.large
export MASTER_COUNT=3
export MASTER_ZONES=us-east-1a,us-east-1c,us-east-1e

export NODE_SIZE=r4.x2large
export NODE_COUNT=2
# to find valid availability zones, use following command
# aws ec2 describe-availability-zones
export ZONES=us-east-1a,us-east-1c,us-east-1d,us-east-1e

export DNS_ZONE=
export CLUSTER_NAME=$DNS_ZONE
export KOPS_STATE_STORE=s3://$DNS_ZONE

export VPC=
export NETWORK_CIDR=

export AWS_DEFAULT_REGION=us-east-1
export AWS_DEFAULT_PROFILE=

export AUTHORIZATION=
export CLOUD_LABELS=
export ADMIN_ACCESS=

export IMAGE=
```

Most these variables are just used by kops when creating the cluster, which is wrapped by aladdin. If you need more info, check [here](https://github.com/kubernetes/kops/blob/master/docs/cli/kops_create_cluster.md). Note that the env.sh in your LOCAL folder will be mostly empty since you are not actually creating a cluster in that scenario.

## Cluster config.json file
The config.json file in each of your subdirectories in your config folder will contain cluster-specific configuration for your aladdin installation. Here is an example config.json file for a specific cluster:

```jsonc
{
    "aws_profile": "abcdefgh",
    "cluster_name": "CLUSTERDEV",
    "certificate_lookup": true,  // optional, defaults to true
    "root_dns": "clusterdev.exampledev.info",
    "service_dns_suffix": "exampletest.com",
    "allowed_namespaces": [
        "default", "kube-system"
    ],
    "cluster_init": [
        {"project": "dashboard", "ref": "v1.0.0", "namespace": "kube-system"}
    ],
    "dual_dns_prefix_annotation_name": "dns-name"
}
```
- aws_profile section: which aws profile you are interacting with for the cluster
- cluster_name section: the name of your cluster. This will match the name of the subdirectory in most cases.
- root_dns section: the dns for your cluster. This should match the DNS_ZONE from your env.sh file in most cases. This is used by aladdin when it maps dns for each of your externally accessible services.
- service_dns_suffix section: aladdin maps your services to `{service name}.{namespace}.{root_dns}`, and thus, will request a certificate for `*.{namespace}.{root_dns}`. By setting this, it will instead request a certificate for `*.{service_dns_suffix}`. Note that you will still need manually to map your service from `{service name}.{service_dns_suffix}` to `{service name}.{namespace}.{root_dns}`.
- allowed_namespaces section: which namespaces you are allowed to interact with in this cluster
- check_branch section (not shown in example): which branch on your remote repo to check against before deploying (e.g. set this to master for your production cluster)
- cluster_init section: which projects to install when running `aladdin cluster init`. You must specify the project, ref, and namespace.
- namespace_init section (not shown in example): whenever a namespace is created, install any projects in this section. You must specify a project and a ref.
- dual_dns_prefix_annotation_name section: you can use this annotation (in this example, it is "dns-name") in your service.yaml files to change the prefix for the dns your service is mapped to
- certificate_lookup section: determines if aladdin should lookup acm certificates to inject into helm charts (optional, defaults to `true`).

Note: Aladdin also supports a `default/` folder which can have a `config.json` file that other clusters will inherit from.

Note: Aladdin allows you to override configuration on a namespace level as well. To do this, create a namespace-overrides folder in your cluster subdirectory folder, and create a folder for each namespace you want to override config for. Then create a `config.json` file with any overrides. See the `config-example/CLUSTERDEV/namespace-overrides/test/config.json` file for an example.

## Cluster values.yaml file
The values.yaml file in each of your subdirectories in your config folder will contain cluster-specific values which will be set for all helm charts in this cluster when running `aladdin deploy` or `aladdin start`. Here is an example values.yaml file for a LOCAL cluster:

```yaml
service:
  publicServiceType: "NodePort"
  certificateArn: "no-certificate-on-local"

deploy:
  ecr:
  imagePullPolicy: "IfNotPresent"
```

Note: Aladdin supports a `values.yaml` file in the "default" directory as well as in namespace-override sub-directories.
