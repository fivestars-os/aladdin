# Aladdin Tail
Tail is an aladdin command used to tail logs from multiple pods.
This command can be called from anywhere.
The command can either tail logs from all pods belonging to a specific deployment with `--deployment <DEPLOYMENT>`, or from a single pod with the `--pod <POD>` option. These two options are mutually exclusive, with deployment being the default behavior. The flags may be set without providing the name of their the deployment or pod. In this case, all possible deployments or pods will be listed and the user will be able to choose.

The user may also specify the container they wish to tail logs for with `--container <CONTAINER>`. If not specified and there are more than 1 containers to choose from, all container options are listed and the user is given an option to choose. Only one container may be tailed.

If tailing more than one pod, the pod names may be color-coded. The color options are as follows:
- pod (default): Only the pod name is colorized but the logged text is using the terminal default color
- line: The entire line is colorized
- false: Do not colorize output at all

Usage: `aladdin [-c <CLUSTER>] [-n <NAMESPACE>] tail [--deployment <DEPLOYMENT>] [--pod <POD>] [--container <CONTAINER> ] [--color <COLOR>]`

- if `--pod` flag is not set, default to tailing all pods for a deployment
- if deployment/pod or containers are not supplied, show all possible options
- can be used with `-c` and `-n` to connect to containers in other clusters

```
  > aladdin tail

Available Deployments:
--------------------
0: deployment aladdin-demo-commands
1: deployment aladdin-demo-redis
2: deployment aladdin-demo-server
Choose index for the deployment to tail logs for: 2
0: container aladdin-demo-uwsgi
1: container aladdin-demo-nginx
Choose index for the container to tail logs for: 0
Will tail 3 logs...
aladdin-demo-server-1545458001-11r82
aladdin-demo-server-1545458001-4gq8p
aladdin-demo-server-1545458001-vzgl5
```

```
  > aladdin tail --deployment aladdin-demo-server --container aladdin-demo-nginx --color line
Will tail 3 logs...
aladdin-demo-server-1545458001-11r82
aladdin-demo-server-1545458001-4gq8p
aladdin-demo-server-1545458001-vzgl5
```

```
  > aladdin tail --pod
Available Pods:
---------------
0: pod: aladdin-demo-commands-3371800710-vh12v
1: pod: aladdin-demo-elasticsearch-0
2: pod: aladdin-demo-redis-356516715-clxnw
3: pod: aladdin-demo-server-1545458001-11r82
4: pod: aladdin-demo-server-1545458001-4gq8p
5: pod: aladdin-demo-server-1545458001-vzgl5
Choose index for the pod to tail logs for: 0
Will tail 1 logs...
aladdin-demo-commands-3371800710-vh12v
```

Thank you to github user johanhaleby for your [kubetail script](https://github.com/johanhaleby/kubetail/blob/b333cc8a1d87a593b8bc3b80f7dfaa04947f39e8/kubetail) which we have incorporated into this command
