import os
import subprocess
import sys
from urllib.parse import urlparse

from aladdin.lib.arg_tools import expand_namespace, container_command
from aladdin.lib.aws.certificate import get_cluster_certificate_arn, get_service_certificate_arn
from aladdin.lib.cluster_rules import ClusterRules
from aladdin.lib.git import Git
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.publish_rules import PublishRules


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "helm-values", help="Start the helm chart in non local environments",
    )
    subparser.set_defaults(func=helm_values)
    subparser.add_argument("uri", help="which project to deploy")


@container_command
@expand_namespace
def helm_values(
    uri,
):
    uri = urlparse(uri)
    os.environ["CLUSTER_CODE"] = uri.netloc
    ARGOCD_APP_NAME = os.getenv("ARGOCD_APP_NAME") or "mission-control"
    NAMESPACE = os.getenv("HELM_NAMESPACE") or os.getenv("ARGOCD_APP_NAMESPACE") or "default"
    ARGOCD_APP_REVISION = os.getenv("ARGOCD_APP_REVISION") or "main"
    git_ref = ARGOCD_APP_REVISION[:Git.SHORT_HASH_SIZE]
    cr = ClusterRules(namespace=NAMESPACE)
    pr = PublishRules()

    values = {
        "deploy.ecr": pr.docker_registry,
        "deploy.namespace": NAMESPACE,
        "project.name": ARGOCD_APP_NAME,
        "service.certificateScope": cr.service_certificate_scope,
        "service.domainName": cr.service_domain_name_suffix,
        "service.clusterCertificateScope": cr.cluster_certificate_scope,
        "service.clusterDomainName": cr.cluster_domain_name_suffix,
        "service.clusterName": cr.cluster_domain_name,  # aka root_dns
    }
    if cr.certificate_lookup:
        values.update({
            "service.certificateArn": get_service_certificate_arn(),
            "service.clusterCertificateArn": get_cluster_certificate_arn(),
        })
    # Update with cluster rule values
    values.update(cr.values)


    args = [
        f"--values={f}" for f in Helm().find_values("helm/mission-control", cr.cluster_name, NAMESPACE)
    ]
    for key, value in values.items():
        args.extend(["--set", f"{key}={value}"])

    subprocess.run(
        ["helm", "merge-values", *args, "--set-string", f"deploy.imageTag={git_ref}"],
        capture_output=False,
        check=True,
    )

