import os
import logging
import time

from aladdin.lib.k8s.kubernetes import KubernetesException


class KubernetesUtils(object):
    """
    Put code here that does not directly wrap kubernetes python library
    """

    def __init__(self, k8s):
        self.k8s = k8s

    def _update_mapping(self, service_map, service, dns_value, dual_dns_prefix_annotation_name):
        # check duplicate entries
        if service.metadata.name in service_map:
            raise Exception("Duplicate service name %s" % service.metadata.name)

        if dual_dns_prefix_annotation_name:
            try:
                annotation_dns = service.metadata.annotations[dual_dns_prefix_annotation_name]
            except (AttributeError, KeyError, TypeError):
                pass  # annotation_dns not present
            else:
                if annotation_dns in service_map:
                    raise Exception("Duplicate annotated service name %s" % service.metadata.name)
                service_map[annotation_dns] = dns_value

        service_map[service.metadata.name] = dns_value

    def get_services_to_load_balancers_map(self, dual_dns_prefix_annotation_name, ingress_info):
        """
        Maps service names to their load balancer dns. If no load balancer
        present and service type is NodePort, it attempts to map the service
        name to the ingress dns. All other services are mapped to None.
        :param list of service items returned by api.list_namespaced_service
        :return dict: service_name (str) -> load_balancer_dns_name (str)
        """
        services = self.k8s.get_services()
        service_map = {}

        # Map all services of type loadBalancer to their elb hostname
        for service in filter(lambda s: s.spec.type == "LoadBalancer", services):
            load_balancer_dns = self._get_load_balancer_hostname_with_retry(service.metadata.name)
            self._update_mapping(
                service_map, service, load_balancer_dns, dual_dns_prefix_annotation_name
            )

        # If ingress is turned on, map all services of type nodePort to the ingress controller
        # service elb hostname
        if ingress_info and ingress_info["use_ingress_per_namespace"]:
            ingress_controller_service_name = ingress_info["ingress_controller_service_name"]

            # Get ingress controller dns
            ingress_services = [
                service
                for service in services
                if service.metadata.name == ingress_controller_service_name
            ]
            if len(ingress_services) != 1:
                raise KubernetesException(
                    "Expected exactly 1 service with name {0}. Got {1}.".format(
                        ingress_controller_service_name, len(ingress_services)
                    )
                )
            else:
                ingress_dns = self._get_load_balancer_hostname_with_retry(
                    ingress_services[0].metadata.name
                )

            # Map NodePort services to ingress dns
            for service in filter(lambda s: s.spec.type == "NodePort", services):
                self._update_mapping(
                    service_map, service, ingress_dns, dual_dns_prefix_annotation_name
                )

        return service_map

    def _get_load_balancer_hostname_with_retry(self, service_name):
        load_balancers = None
        retry_count = 0
        while retry_count < 20:
            services = [
                service
                for service in self.k8s.get_services()
                if service_name == service.metadata.name
            ]
            if len(services) != 1:
                raise KubernetesException(
                    "Expected one service with name {0}, got {1}".format(
                        service_name, len(services)
                    )
                )
            load_balancers = services[0].status.load_balancer.ingress
            if load_balancers is not None:
                break
            time.sleep(1)
            retry_count += 1
        if load_balancers is None:
            logging.warning(
                "Failed to map dns to {} load balancer because load balancer was not"
                " ready.".format(service_name)
            )
            logging.warning(
                "Please Try again in a few moments by calling `aladdin -c {0} -n {1}"
                " sync-dns`.".format(os.getenv("CLUSTER_CODE"), os.getenv("NAMESPACE"))
            )
            return
        elif len(load_balancers) != 1:
            raise KubernetesException(
                "Expected 1 load balancer for {0}. Got {1}.".format(
                    service_name, len(load_balancers)
                )
            )
        else:
            return load_balancers[0].hostname
