import os
from contextlib import suppress

from .aws.certificate import get_cluster_certificate_arn, get_service_certificate_arn
from .cluster_rules import ClusterRules
from .project_conf import ProjectConf
from .utils import strtobool


class HelmRules:
    debug = strtobool(os.getenv("HELM_DEBUG", "false"))

    @staticmethod
    def get_release_name(chart_name: str):
        # TODO there is a limit on the name size, we should check that
        return f"{chart_name}-{ClusterRules().namespace}"

    @staticmethod
    def get_helm_values():
        values = {
            "deploy.namespace": ClusterRules().namespace,
            "service.certificateScope": ClusterRules().service_certificate_scope,
            "service.domainName": ClusterRules().service_domain_name_suffix,
            "service.clusterCertificateScope": ClusterRules().cluster_certificate_scope,
            "service.clusterDomainName": ClusterRules().cluster_domain_name_suffix,
            "service.clusterName": ClusterRules().cluster_domain_name,  # aka root_dns
        }
        if ClusterRules().certificate_lookup:
            values.update(
                {
                    "service.certificateArn": get_service_certificate_arn(),
                    "service.clusterCertificateArn": get_cluster_certificate_arn(),
                }
            )

        with suppress(FileNotFoundError):
            values.update(
                {
                    "project.name": ProjectConf().name,
                }
            )

        values.update(ClusterRules().values)

        return values
