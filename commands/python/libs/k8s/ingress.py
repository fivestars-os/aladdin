from kubernetes import client


def _create_ingress_service_tuples(services, dual_dns_prefix_annotation_name):
    service_tuples_dict = {}
    # remove non NodePort services
    services = [s for s in services if s.spec.type == "NodePort"]

    for service in services:
        for port_object in service.spec.ports:
            port = port_object.port
            name_port = "%s:%s" % (service.metadata.name, port)
            # create service tuple from default service name
            service_tuples_dict[name_port] = (service.metadata.name, port, service)
            if dual_dns_prefix_annotation_name:
                try:
                    # create service tuple from annotation dns
                    annotation_name = service.metadata.annotations[dual_dns_prefix_annotation_name]
                except (AttributeError, KeyError, TypeError):
                    pass  # no annotation found
                else:
                    name_port = "%s:%s" % (annotation_name, port)
                    service_tuples_dict[name_port] = (annotation_name, port, service)

    return list(service_tuples_dict.values())


def build_ingress(services, dns_suffix, dual_dns_prefix_annotation_name, ingress_info):
    ingress = client.ExtensionsV1beta1Ingress()
    # init metadata
    ingress.metadata = client.V1ObjectMeta()
    ingress.metadata.name = ingress_info["ingress_name"]
    # init spec
    ingress.spec = client.ExtensionsV1beta1IngressSpec()
    ingress.spec.rules = []
    service_tuples = _create_ingress_service_tuples(services, dual_dns_prefix_annotation_name)
    for dns_prefix, port, service in service_tuples:
        ingress_rule = client.ExtensionsV1beta1IngressRule()
        ingress_rule.host = "%s.%s" % (dns_prefix, dns_suffix)
        backend = client.ExtensionsV1beta1IngressBackend(
            service_name=service.metadata.name, service_port=port
        )
        ingress_path = [client.ExtensionsV1beta1HTTPIngressPath(path="/", backend=backend)]
        ingress_rule.http = client.ExtensionsV1beta1HTTPIngressRuleValue(ingress_path)

        ingress.spec.rules.append(ingress_rule)

    if not ingress.spec.rules:
        ingress_dummy_backend = client.ExtensionsV1beta1IngressBackend(
            service_name=ingress_info["ingress_controller_service_name"], service_port=80
        )
        ingress.spec.backend = ingress_dummy_backend

    return ingress
