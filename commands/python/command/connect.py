#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from libs.k8s.kubernetes import Kubernetes


def parse_args(sub_parser):
    subparser = sub_parser.add_parser('connect', help='Connect to a container')
    subparser.set_defaults(func=connect_args)
    subparser.add_argument('app', default=None, nargs='?', help='which app to connect to')
    add_namespace_argument(subparser)


def connect_args(args):
    connect(args.app, args.namespace)


def connect(app_name, namespace=None):
    k = Kubernetes(namespace=namespace)
    pods = k.get_pods(app_name)
    bash_else_sh = ["sh", "-c", "which bash >/dev/null && exec bash || exec sh"]

    if len(pods) == 1 and len(pods[0].status.container_statuses) == 1:
        # only 1 possible pod and container
        k.kub_exec(pods[0].metadata.name, pods[0].status.container_statuses[0].name, *bash_else_sh)
        return

    print("\r\nAvailable:")
    print("----------")
    idx = 0
    pod_container_pairs = []
    for pod in pods:
        for container in pod.status.container_statuses or []:
            print('{idx}: pod {pod_name}; container {container_name}'
                  .format(idx=idx, pod_name=pod.metadata.name, container_name=container.name))
            pod_container_pairs.append((pod.metadata.name, container.name))
            idx += 1

    idx_input = input("Choose an index:  ")
    try:
        idx = int(idx_input)
    except ValueError:
        print("Invalid index value '%s'" % (idx_input,))
        return
    pair = pod_container_pairs[idx]

    k.kub_exec(pair[0], pair[1], *bash_else_sh)
