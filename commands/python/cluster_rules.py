#!/usr/bin/env python3
import boto3

from libs.aws.certificate import search_certificate_arn, new_certificate_arn
from libs.aws.dns_mapping import (
    get_hostedzone,
    create_hostedzone,
    get_ns_from_hostedzone,
    check_ns_values,
    fill_dns_dict,
)

from config import *


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
    def namespace(self):
        return self._namespace

    @property
    def global_namespace(self):
        return self.values.get("service.global_namespace", "default")

    def get_certificate_arn(self, get_root=False):
        cert = self.values.get("service.certificateArn")

        # Check against None to allow empty string
        if cert is None:
            certificate_dns = self.root_certificate_dns if get_root else self.certificate_dns
            cert = search_certificate_arn(self._boto, certificate_dns)

        # Check against None to allow empty string
        if cert is None:
            cert = new_certificate_arn(self._boto, certificate_dns)

        return cert

    @property
    def root_certificate_dns(self):
        return "*.{}".format(self.root_dns_suffix)

    @property
    def certificate_dns(self):
        return "*.{}".format(self.service_dns_suffix)

    @property
    def root_dns_suffix(self):
        """
        The "top-level" DNS name for the cluster services.

        If "service_dns_suffix" is defined in the cluster config, that value will be used instead.
        """
        return self.rules.get("service_dns_suffix", self.root_dns)

    @property
    def service_dns_suffix(self):
        return self.rules.get("service_dns_suffix", self.sub_dns)

    @property
    def sub_dns(self):
        """
        The dns we are going to use
        """
        return "{}.{}".format(self._namespace, self.root_dns)

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
    def _boto(self):
        return boto3.Session(profile_name=self.aws_profile)

    def fill_hostedzone(self, services_by_name):
        # Apply our dns to the names
        service_by_name = {"%s.%s" % (k, self.sub_dns): v for k, v in services_by_name.items()}

        # Main DNS is on prod, sub DNS should be on sandbox
        sub_dns_id = get_hostedzone(self._boto, self.sub_dns) or create_hostedzone(
            self._boto, self.sub_dns
        )
        main_dns_id = get_hostedzone(self._boto, self.root_dns)
        if main_dns_id is None:
            raise KeyError("route 53 for [%s] not found" % self.root_dns)

        dns_ns = get_ns_from_hostedzone(self._boto, sub_dns_id)
        check_ns_values(self._boto, main_dns_id, self.sub_dns, dns_ns)

        return fill_dns_dict(self._boto, sub_dns_id, service_by_name)


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
    _update_rules(rules, cluster_config)
    if namespace_override_config:
        _update_rules(rules, namespace_override_config)

    allowed_namespaces = rules["allowed_namespaces"]
    if allowed_namespaces != ["*"] and namespace not in allowed_namespaces:
        raise KeyError(f"Namespace {namespace} is not allowed on cluster {cluster}")

    return ClusterRules(rules, namespace)


def _update_rules(rules, override):
    # Update values separately and save it in values variable since it's an inner dictionary
    values = rules.get("values", {})
    values.update(override.get("values", {}))

    rules.update(override)

    # Put back updated values
    rules["values"] = values
