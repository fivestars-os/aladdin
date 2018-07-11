# Aladdin Connect
Connect is one of aladdin's commands used to connect to a container's shell. This command finds the pods related to a supplied deployment name. If only one pod with a single container is found, it connects directly to that container's shell. We first try `bash`, but if that doesn't work, we settle on `sh`. If multiple pods-container pairs are found that contain the supplied deployment name, they are all listed, and an index must be chosen. 
```
usage: aladdin connect [-h] [--namespace NAMESPACE] [app]

positional arguments:
  app                   which app to connect to

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
```
Example:
```
  > aladdin connect aladdin-demo-server

Available:
----------
0: pod aladdin-demo-server-786c967bff-xlfrs; container aladdin-demo-nginx
1: pod aladdin-demo-server-786c967bff-xlfrs; container aladdin-demo-uwsgi
2: pod aladdin-demo-server-f66fb6c5d-754pv; container aladdin-demo-nginx
3: pod aladdin-demo-server-f66fb6c5d-754pv; container aladdin-demo-uwsgi
Choose an index:
```
