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
                    annotation_name = service.metadata.annotations[
                        dual_dns_prefix_annotation_name
                    ]
                except (AttributeError, KeyError, TypeError):
                    pass  # no annotation found
                else:
                    name_port = "%s:%s" % (annotation_name, port)
                    service_tuples_dict[name_port] = (annotation_name, port, service)

    return list(service_tuples_dict.values())


def build_ingress(services, dns_suffix, dual_dns_prefix_annotation_name, ingress_info):
    ingress = client.V1Ingress()
    # init metadata
    ingress.metadata = client.V1ObjectMeta()
    ingress.metadata.name = ingress_info["ingress_name"]
    # init spec
    ingress.spec = client.V1IngressSpec()
    ingress.spec.rules = []
    service_tuples = _create_ingress_service_tuples(
        services, dual_dns_prefix_annotation_name
    )
    # A little bit of a hack to have the ingress put the port:443 entries before the port:80 entries,
    # so that the port:80 entries take precedence if the service name is the same. Without this
    # we get ssl errors when accessing services behind the ingress locally because of k3d internals
    service_tuples = sorted(service_tuples, key=lambda x: x[1], reverse=True)
    for dns_prefix, port, service in service_tuples:
        ingress_rule = client.V1IngressRule()
        ingress_rule.host = "%s.%s" % (dns_prefix, dns_suffix)
        backend = client.V1IngressBackend(
            service=client.V1IngressServiceBackend(
                port=client.V1ServiceBackendPort(
                    number=port,
                ),
                name=service.metadata.name,
            )
        )
        ingress_rule.http = client.V1HTTPIngressRuleValue([
            client.V1HTTPIngressPath(
                path="/", backend=backend, path_type="ImplementationSpecific"
            )
        ])

        ingress.spec.rules.append(ingress_rule)

    if not ingress.spec.rules:
        ingress.spec.default_backend = client.V1IngressBackend(
            service=client.V1IngressServiceBackend(
                port=client.V1ServiceBackendPort(
                    number=80,
                ),
                name=ingress_info["ingress_controller_service_name"],
            )
        )

    return ingress
