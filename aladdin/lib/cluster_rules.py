import os
import boto3

from aladdin.lib.aws.certificate import search_certificate_arn, new_certificate_arn
from aladdin.config import load_cluster_config, load_namespace_override_config


class ClusterRules(object):
    def __init__(self, rules, namespace="default"):
        self.rules = rules
        self._namespace = namespace

    def __getattr__(self, attr):
        if attr in self.rules:
            return self.rules.get(attr)
        raise AttributeError(
            "'{}' object has no attribute '{}'".format(self.__class__.__name__, attr)
        )

    @property
    def service_certificate_arn(self):
        return self._get_certificate_arn(self.service_certificate_scope)

    @property
    def cluster_certificate_arn(self):
        return self._get_certificate_arn(self.cluster_certificate_scope)

    def _get_certificate_arn(self, certificate_scope):
        cert = self.values.get("service.certificateArn")

        # Check against None to allow empty string
        if cert is None:
            cert = search_certificate_arn(self.boto, certificate_scope)

        # Check against None to allow empty string
        if cert is None:
            cert = new_certificate_arn(self.boto, certificate_scope)

        return cert

    @property
    def cluster_certificate_scope(self):
        return "*.{}".format(self.cluster_domain_name_suffix)

    @property
    def service_certificate_scope(self):
        return "*.{}".format(self.service_domain_name_suffix)

    @property
    def cluster_domain_name_suffix(self):
        """
        The "top-level" DNS name for the cluster services.

        Will be "root_dns" from the cluster config unless "service_dns_suffix" is defined,
        in which case the latter will be used.
        """
        return self.rules.get("service_dns_suffix", self.cluster_domain_name)

    @property
    def service_domain_name_suffix(self):
        return self.rules.get("service_dns_suffix", self.namespace_domain_name)

    @property
    def cluster_domain_name(self):
        """
        Alias to aladdin "root_dns" config value.

        "root_dns" has other denotations that are not helpful in this context. We can at least use
        more appropriate terminology here in the code.
        """
        return self.root_dns

    @property
    def namespace_domain_name(self):
        """
        The dns we are going to use
        """
        return "{}.{}".format(self.namespace, self.cluster_domain_name)

    @property
    def namespace(self):
        return self._namespace

    @property
    def check_branch(self):
        return self.rules.get("check_branch", None)

    @property
    def is_local(self):
        return self.rules.get("is_local", False)

    @property
    def is_prod(self):
        return self.rules.get("is_prod", False)

    @property
    def ingress_info(self):
        return self.rules.get("ingress_info", None)

    @property
    def namespace_init(self):
        return self.rules.get("namespace_init", [])

    @property
    def cluster_init(self):
        return self.rules.get("cluster_init", [])

    @property
    def dual_dns_prefix_annotation_name(self):
        return self.rules.get("dual_dns_prefix_annotation_name", None)

    @property
    def boto(self):
        return boto3.Session(profile_name=self.aws_profile)


def cluster_rules(cluster=None, namespace="default"):

    if cluster is None:
        cluster = os.environ["CLUSTER_CODE"]

    default_cluster_config = {}
    cluster_config = {}
    namespace_override_config = {}

    try:
        default_cluster_config = load_cluster_config("default")
    except FileNotFoundError:
        pass

    try:
        cluster_config = load_cluster_config(cluster)
    except FileNotFoundError:
        raise FileNotFoundError(f"Could not find config.json file for cluster {cluster}")

    try:
        namespace_override_config = load_namespace_override_config(cluster, namespace)
    except FileNotFoundError:
        pass

    rules = dict(default_cluster_config)
    rules.update(rules, cluster_config)
    if namespace_override_config:
        rules.update(namespace_override_config)

    allowed_namespaces = rules["allowed_namespaces"]
    if allowed_namespaces != ["*"] and namespace not in allowed_namespaces:
        raise KeyError(f"Namespace {namespace} is not allowed on cluster {cluster}")

    return ClusterRules(rules, namespace)
