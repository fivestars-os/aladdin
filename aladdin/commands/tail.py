import logging

from aladdin.arg_tools import add_namespace_argument, container_command
from aladdin.lib.k8s.kubernetes import Kubernetes


def parse_args(sub_parser):
    subparser = sub_parser.add_parser("tail", help="Tail logs of multiple pods")
    subparser.set_defaults(func=tail_args)
    subparser.add_argument(
        "--container", default=None, nargs="?", help="which container to view logs for"
    )
    subparser.add_argument(
        "--color",
        default="pod",
        nargs="?",
        choices=["pod", "line", "false"],
        help=(
            "specify how to colorize the logs, defaults to 'pod'."
            " Options:"
            " pod: Only the pod name is colorized, but the logged"
            " text uses the terminal default color."
            " line: The entire line is colorized."
            " false: Do not colorize output at all"
        ),
    )
    add_namespace_argument(subparser)
    pod_group = subparser.add_mutually_exclusive_group()
    pod_group.add_argument(
        "--deployment",
        action="store",
        nargs="?",
        const="",
        default=None,
        help="deployment name for pods to view logs for",
    )
    pod_group.add_argument(
        "--pod",
        action="store",
        nargs="?",
        const="",
        default=None,
        help="full name of pod to view logs for",
    )


def tail_args(args):
    tail(args.container, args.color, args.deployment, args.pod, args.namespace)


@container_command
def tail(container_name, color, deployment_name, pod_name, namespace=None):
    k = Kubernetes(namespace=namespace)
    deployment, pod = None, None
    if pod_name is not None:
        if pod_name == "":
            pod = choose_pod(k)
            pod_name = pod.metadata.name
        else:
            try:
                pod = k.get_pod_by_name(pod_name)
            except IndexError:
                logging.warning(
                    "Could not find pod with given name, please choose from the available pods"
                )
                pod = choose_pod(k)
                pod_name = pod.metadata.name
    else:
        if not deployment_name:
            deployment = choose_deployment(k)
            deployment_name = deployment.metadata.name
        else:
            deployment = k.get_deployment(deployment_name)
            if deployment is None:
                logging.warning(
                    "Could not find deployment with given app name, please choose from "
                    "the available deployments"
                )
                deployment = choose_deployment(k)
                deployment_name = deployment.metadata.name
    if not container_name:
        containers = print_containers(k, deployment=deployment, pod=pod)
        if len(containers) == 1:
            container = containers[0]
        else:
            idx = int(input("Choose index for the container to tail logs for: "))
            container = containers[idx]
        container_name = container.name

    k.tail_logs(
        deployment_name=deployment_name,
        pod_name=pod_name,
        container_name=container_name,
        color=color,
    )


def choose_pod(k):
    pods = print_pods(k)
    idx = int(input("Choose index for the pod to tail logs for: "))
    return pods[idx]


def choose_deployment(k):
    deployments = print_deployments(k)
    idx = int(input("Choose index for the deployment to tail logs for: "))
    return deployments[idx]


def print_deployments(k):
    deployments = k.get_deployments()
    print("\r\nAvailable Deployments:")
    print("--------------------")
    idx = 0
    for deployment in deployments:
        print("{idx}: deployment {deployment}".format(idx=idx, deployment=deployment.metadata.name))
        idx += 1
    return deployments


def print_pods(k):
    pods = k.get_pods()
    print("\r\nAvailable Pods:")
    print("---------------")
    idx = 0
    for pod in pods:
        print("{idx}: pod: {pod_name}".format(idx=idx, pod_name=pod.metadata.name))
        idx += 1
    return pods


def print_containers(k, deployment=None, pod=None):
    if deployment:
        containers = deployment.spec.template.spec.containers
    elif pod:
        containers = pod.spec.containers
    if len(containers) == 1:
        return containers
    idx = 0
    for container in containers:
        print("{idx}: container {container}".format(idx=idx, container=container.name))
        idx += 1
    return containers
