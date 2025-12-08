#!/usr/bin/env python3
import os
import subprocess

from kubernetes import client, config
from kubernetes.client import configuration

from aladdin.lib.arg_tools import get_current_namespace


class KubernetesException(Exception):
    pass


class Kubernetes(object):
    """
    Use this class to define methods that esentially wrap the kubernetes python lib
    For more involved functions, you may want to put them in the KubernetesUtil class
    kubectl exec calls are the only ones currently not wrapping the python library
    """

    def __init__(
        self,
        default_component_label=None,
        default_project_label=None,
        namespace=None,
        kubeconfig=None,
    ):
        self.default_component_label = default_component_label or "app"
        self.default_project_label = default_project_label or "project"
        self.kubeconfig = kubeconfig or os.getenv("KUBECONFIG")
        try:
            config.load_kube_config(self.kubeconfig)
        except Exception:
            try:
                config.load_incluster_config()  # How to set up the client from within a k8s pod
            except config.config_exception.ConfigException:
                raise KubernetesException(
                    "Could not configure kubernetes python client"
                )
        configuration.assert_hostname = False
        self.core_v1_api = client.CoreV1Api()
        self.apps_v1_api = client.AppsV1Api()
        self.networking_v1_api = client.NetworkingV1Api()
        self.namespace = namespace or get_current_namespace()

    def _kub_cmd(self, *args):
        # For commands that use kubectl - only exec is left
        res = ["kubectl", "--namespace=" + self.namespace]
        if self.kubeconfig:
            res.append("--kubeconfig=" + self.kubeconfig)
        res.extend(args)
        return res

    def kub_exec(
        self, pod_name, container_name, *command, return_output=False, terminal=True
    ):
        # TODO: this function does not work with kubernetes python client yet,
        # so we are using subprocess with kubectl here. When it does work, try below
        # kube_api_client.connect_get_namespaced_pod_exec(pod_name, namespace,
        # container=container_name, command="/bin/bash", stderr=True, stdin=True, stdout=True,
        # tty=True)

        # Returns kubectl exec -it pod_name -c container_name *command. Use container_name as None
        # if you do not need to specify container_name (for single container pods)
        if terminal:
            flags = "-it"
        else:
            flags = "-i"

        if container_name:
            cmd_list = self._kub_cmd(
                "exec", flags, pod_name, "-c", container_name, "--", *command
            )
        else:
            cmd_list = self._kub_cmd("exec", flags, pod_name, "--", *command)

        if return_output:
            with open(os.devnull, "w") as devnull:
                return subprocess.check_output(cmd_list, stderr=devnull)
        subprocess.check_call(cmd_list)

    def get_objects(self, obj_type, label_val=None, label_key=None):
        # obj_type should be the full name singular of the object, i.e. pod, secret, service, deploy
        # Check https://github.com/kubernetes-incubator/client-python/blob/master/kubernetes/
        # docs/CoreV1Api.md if you are not sure
        if not label_key:
            label_key = self.default_component_label
        get_func_name = "list_namespaced_%s" % obj_type
        # Ingress and Deployment are the only k8s objs we care about not in the core_v1_api for
        # some reason, so we use other appropriate clients here
        if obj_type == "deployment":
            get_func = getattr(self.apps_v1_api, get_func_name)
        elif obj_type == "ingress":
            get_func = getattr(self.networking_v1_api, get_func_name)
        else:
            get_func = getattr(self.core_v1_api, get_func_name)
        # Create a label selector filter if label_val was specified
        label_selector = ""
        # Check if we have multiple label/selector pairs
        if type(label_key) is list and type(label_val) is list:
            if len(label_key) != len(label_val):
                raise KubernetesException(
                    "Error in calling get_objects in class Kubernetes with "
                    "different number of label keys than label values"
                )
            label_selector = ",".join(
                ["{0}={1}".format(x[0], x[1]) for x in zip(label_key, label_val)]
            )
        elif label_val:
            label_selector = "{0}={1}".format(label_key, label_val)
        objs = get_func(self.namespace, label_selector=label_selector).items
        return objs

    def get_pods(self, label_val=None, label_key=None):
        return self.get_objects("pod", label_val, label_key)

    def get_pod(self, label_val=None, label_key=None, default=None):
        return (self.get_pods(label_val, label_key) + [default])[0]

    def get_pod_name(self, label_val=None, label_key=None, default=None):
        pod = self.get_pod(label_val, label_key)
        # Return pod name if it is not None, else return default
        return pod and pod.metadata.name or default

    def get_services(self, label_val=None, label_key=None):
        return self.get_objects("service", label_val, label_key)

    def get_service(self, label_val=None, label_key=None, default=None):
        return (self.get_services(label_val, label_key) + [default])[0]

    def get_ingresses(self, label_val=None, label_key=None):
        return self.get_objects("ingress", label_val, label_key)

    def get_ingress(self, label_val=None, label_key=None, default=None):
        return (self.get_ingresses(label_val, label_key) + [default])[0]

    def create_ingress(self, body):
        self.networking_v1_api.create_namespaced_ingress(self.namespace, body)

    def update_ingress(self, name, body):
        self.networking_v1_api.patch_namespaced_ingress(name, self.namespace, body)

    def delete_ingress(self, name):
        self.networking_v1_api.delete_namespaced_ingress(
            name, self.namespace, body=client.V1DeleteOptions()
        )
