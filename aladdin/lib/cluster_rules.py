import os
from typing import List

import boto3

try:
    from functools import cached_property
except ImportError:
    # Running on pre-3.8 Python; use backport
    from backports.cached_property import cached_property

from aladdin.config import load_cluster_config, load_namespace_override_config
from aladdin.lib.arg_tools import get_current_namespace
from aladdin.lib.utils import strtobool


class ClusterRules:
    def __init__(self, cluster=None, namespace=None):
        self.rules = _cluster_rules(cluster=cluster, namespace=namespace)
        self._namespace = namespace or get_current_namespace()

    def __getattr__(self, attr):
        if attr in self.rules:
            return self.rules.get(attr)
        raise AttributeError(
            "'{}' object has no attribute '{}'".format(self.__class__.__name__, attr)
        )

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
    def cluster_domain_name(self) -> str:
        """
        Alias to aladdin "root_dns" config value.

        "root_dns" has other denotations that are not helpful in this context. We can at least use
        more appropriate terminology here in the code.
        """
        return self.root_dns

    @property
    def values_files(self) -> List[str]:
        """
        Alias to aladdin "values_files" config value.

        Defaults to aladdin "cluster_name" config value for backwards compatibility
        """
        return self.rules.get("values_files", [self.cluster_name])

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
        return bool(self.rules.get("check_branch", False))

    @property
    def is_local(self):
        return self.rules.get("is_local", False)

    @property
    def is_prod(self):
        return self.rules.get("is_prod", False)

    @property
    def is_testing(self):
        return self.rules.get("is_testing", False)

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
    def certificate_lookup(self):
        if self.is_local:
            return False
        if strtobool(os.getenv("ALADDIN_DISABLE_CERTIFICATE_LOOKUP", "false")):
            return False
        return self.rules.get("certificate_lookup", True)

    @property
    def certificate_lookup_cache(self):
        if self.is_local:
            return False
        if strtobool(os.getenv("ALADDIN_DISABLE_CERTIFICATE_LOOKUP_CACHE", "false")):
            return False
        return self.rules.get("certificate_lookup_cache", True)

    @property
    def dns_sync(self):
        if self.is_local:
            return False
        if strtobool(os.getenv("ALADDIN_DISABLE_DNS_SYNC", "false")):
            return False
        return self.rules.get("dns_sync", True)

    @cached_property
    def boto(self):
        return boto3.Session(profile_name=self.aws_profile)


def _cluster_rules(cluster=None, namespace=None) -> dict:
    if not namespace:
        namespace = get_current_namespace()
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
        raise FileNotFoundError(
            f"Could not find config.json file for cluster {cluster}"
        )

    try:
        namespace_override_config = load_namespace_override_config(cluster, namespace)
    except FileNotFoundError:
        pass

    rules = dict(default_cluster_config)
    _update_rules(rules, cluster_config)
    if namespace_override_config:
        _update_rules(rules, namespace_override_config)

    allowed_namespaces = rules.get("allowed_namespaces", ["*"])
    if allowed_namespaces != ["*"] and namespace not in allowed_namespaces:
        raise KeyError(f"Namespace {namespace} is not allowed on cluster {cluster}")

    return rules


def _update_rules(rules, override):
    # Update values separately and save it in values variable since it's an inner dictionary
    values = rules.get("values", {})
    values.update(override.get("values", {}))

    rules.update(override)

    # Put back updated values
    rules["values"] = values
