#!/usr/bin/env python3
import os
import subprocess
import sys
import time

from kubernetes.client import configuration
from kubernetes import config, client


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
        self.namespace = namespace or os.getenv("NAMESPACE", "default")
        self.kubeconfig = kubeconfig or os.getenv("KUBECONFIG")
        try:
            config.load_kube_config(self.kubeconfig)
        except IOError:
            try:
                config.load_incluster_config()  # How to set up the client from within a k8s pod
            except config.config_exception.ConfigException:
                raise KubernetesException("Could not configure kubernetes python client")
        configuration.assert_hostname = False
        self.core_v1_api = client.CoreV1Api()
        self.apps_v1_beta1_api = client.AppsV1beta1Api()
        self.extensions_v1_beta1_api = client.ExtensionsV1beta1Api()

    def _kub_cmd(self, *args):
        # For commands that use kubectl - only exec is left
        res = ["kubectl", "--namespace=" + self.namespace]
        if self.kubeconfig:
            res.append("--kubeconfig=" + self.kubeconfig)
        res.extend(args)
        return res

    def kub_exec(self, pod_name, container_name, *command, return_output=False, terminal=True):
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
            cmd_list = self._kub_cmd("exec", flags, pod_name, "-c", container_name, "--", *command)
        else:
            cmd_list = self._kub_cmd("exec", flags, pod_name, "--", *command)

        if return_output:
            with open(os.devnull, "w") as devnull:
                return subprocess.check_output(cmd_list, stderr=devnull)
        subprocess.check_call(cmd_list)

    def tail_logs(self, deployment_name=None, pod_name=None, container_name=None, color="pod"):
        # Wrapper around kubetail script to tail logs
        aladdin_dir = os.getenv("ALADDIN_DIR")
        filepath = "{}/scripts/kubetail.sh".format(aladdin_dir)
        # Use stdbuf to bypass default unix buffering behavior for pipes so we can see logs real
        # time
        cmd = ["stdbuf", "-o0", "/bin/bash", filepath]
        if pod_name:
            cmd.append(pod_name)
        if container_name:
            cmd.extend(["-c", container_name])
        if deployment_name:
            cmd.extend(["-l", "app={}".format(deployment_name)])
        cmd.extend(["-k", color])

        # Call kubetail.sh script
        f = subprocess.Popen(cmd, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        for line in f.stdout:
            sys.stdout.write(line.decode("utf-8"))

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
            get_func = getattr(self.apps_v1_beta1_api, get_func_name)
        elif obj_type == "ingress":
            get_func = getattr(self.extensions_v1_beta1_api, get_func_name)
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

    # TODO: make this into a __getattr__ possibly to remove duplicate code
    def get_pods(self, label_val=None, label_key=None):
        return self.get_objects("pod", label_val, label_key)

    def get_pod(self, label_val=None, label_key=None, default=None):
        return (self.get_pods(label_val, label_key) + [default])[0]

    def get_pod_by_name(self, name, default=None):
        return ([pod for pod in self.get_pods() if pod.metadata.name == name] + [default])[0]

    def get_pod_name(self, label_val=None, label_key=None, default=None):
        pod = self.get_pod(label_val, label_key)
        # Return pod name if it is not None, else return default
        return pod and pod.metadata.name or default

    def get_pod_names(self, label_val=None, label_key=None):
        return [pod.metadata.name for pod in self.get_pods(label_val, label_key)]

    def delete_pod(self, name):
        delete_options = client.V1DeleteOptions(propagation_policy="Background")
        self.core_v1_api.delete_namespaced_pod(name, self.namespace, body=delete_options)

    def get_secrets(self, label_val=None, label_key=None):
        return self.get_objects("secret", label_val, label_key)

    def get_secret(self, label_val=None, label_key=None, default=None):
        return (self.get_secrets(label_val, label_key) + [default])[0]

    def get_services(self, label_val=None, label_key=None):
        return self.get_objects("service", label_val, label_key)

    def get_service(self, label_val=None, label_key=None, default=None):
        return (self.get_services(label_val, label_key) + [default])[0]

    def update_service(self, name, body):
        self.core_v1_api.patch_namespaced_service(name, self.namespace, body)

    def get_deployments(self, label_val=None, label_key=None):
        return self.get_objects("deployment", label_val, label_key)

    def get_deployment(self, label_val=None, label_key=None, default=None):
        return (self.get_deployments(label_val, label_key) + [default])[0]

    def get_num_replicas(self, label_val=None, label_key=None, state="ready"):
        deployment_status = self.get_deployment(label_val, label_key).status
        if state == "ready":
            return deployment_status.ready_replicas or 0
        if state == "available":
            return deployment_status.available_replicas or 0
        if state == "desired":
            return deployment_status.replicas or 0
        if state == "updated":
            return deployment_status.updated_replicas or 0
        if state == "unavailable":
            return deployment_status.unavailable_replicas or 0
        raise KubernetesException("Unrecognized state {} for deployment replicas".format(state))

    """
    Wait for deployment with label_key=label_val to reach num_replicas pods. If a max_time is
    specified, and the condition is not met by then, this will return False. Otherwise it will
    return True once the waiting is done.
    """

    def wait_replicas(
        self,
        label_val,
        num_replicas,
        label_key=None,
        retry_interval=5,
        max_time=None,
        state="ready",
        print_updates=True,
    ):
        label_key = label_key or self.default_component_label
        time_waited = 0
        while self.get_num_replicas(label_val, label_key, state) != num_replicas:
            if max_time and time_waited >= max_time:
                return False
            time.sleep(retry_interval)
            time_waited += retry_interval
            if print_updates:
                print(
                    "Waiting for deployment with {0}={1} to scale to {2} pods".format(
                        label_key, label_val, num_replicas
                    )
                )
        return True

    def get_config_maps(self, label_val=None, label_key=None):
        return self.get_objects("config_map", label_val, label_key)

    def get_config_map(self, label_val=None, label_key=None, default=None):
        return (self.get_config_maps(label_val, label_key) + [default])[0]

    def create_config_map(self, name, data, labels=None):
        body = client.V1ConfigMap()
        body.metadata = client.V1ObjectMeta()
        body.metadata.name = name
        if labels:
            body.metadata.labels = labels
        else:
            body.metadata.labels = {self.default_component_label: name}
        body.data = data
        self.core_v1_api.create_namespaced_config_map(self.namespace, body=body)

    def delete_config_map(self, name):
        delete_options = client.V1DeleteOptions(propagation_policy="Background")
        self.core_v1_api.delete_namespaced_config_map(name, self.namespace, body=delete_options)

    def update_config_map(self, name, body):
        # Using replace here because patch doesn't remove keys from a configmap for some reason
        self.core_v1_api.replace_namespaced_config_map(name, self.namespace, body)

    def update_deployment(self, name, body):
        self.apps_v1_beta1_api.patch_namespaced_deployment(name, self.namespace, body)

    # Submit a dummy patch to the deployment to trigger a rolling update on the deployment
    def rolling_update_no_change(self, deployment_name):
        deployment = self.get_deployment(deployment_name)
        deployment.spec.template.metadata.annotations = {
            "aladdin-date-patch": str(int(time.time()))
        }
        self.update_deployment(deployment_name, deployment)

    def get_ingresses(self, label_val=None, label_key=None):
        return self.get_objects("ingress", label_val, label_key)

    def get_ingress(self, label_val=None, label_key=None, default=None):
        return (self.get_ingresses(label_val, label_key) + [default])[0]

    def create_ingress(self, body):
        self.extensions_v1_beta1_api.create_namespaced_ingress(self.namespace, body)

    def update_ingress(self, name, body):
        self.extensions_v1_beta1_api.patch_namespaced_ingress(name, self.namespace, body)

    def delete_ingress(self, name):
        self.extensions_v1_beta1_api.delete_namespaced_ingress(
            name, self.namespace, body=client.V1DeleteOptions()
        )

    def scale(self, deployment, replicas, wait_for=False):
        apps_v1_beta1_client = client.AppsV1beta1Api()
        # create scale object
        scale_obj = client.AppsV1beta1Scale()
        scale_obj.metadata = client.V1ObjectMeta()
        scale_obj.metadata.name = deployment
        scale_obj.metadata.namespace = self.namespace
        scale_obj.spec = client.AppsV1beta1ScaleSpec()
        scale_obj.spec.replicas = replicas

        apps_v1_beta1_client.replace_namespaced_deployment_scale(
            deployment, self.namespace, body=scale_obj
        )

        if wait_for:
            self.wait_replicas(deployment, replicas)
