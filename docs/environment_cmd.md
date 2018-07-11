# Aladdin Environment
Environment is one of aladdin's commands used to get and manipulate config maps. You can optionally provide deployments to refresh (essentially a no-op deploy) after the config map manipulation.    

```
usage: aladdin environment [-h] [--namespace NAMESPACE]
                           [--args ARGS [ARGS ...]]
                           [--refresh [REFRESH [REFRESH ...]]]
                           app {set,unset,get}

positional arguments:
  app                   the values of the label app for the configMap
  {set,unset,get}       how to maniuplate the env

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current : [default]
  --args ARGS [ARGS ...]
                        which key/value pairs to add to environment for set, or which keys to remove from environment for unset
  --refresh [REFRESH [REFRESH ...]]
                        which deployments to refresh

Example usage:
aladdin -c CLUSTER -n NAMESPACE environment CONFIGMAP get
aladdin -c CLUSTER -n NAMESPACE environment CONFIGMAP set --args a=1 b=2 --refresh DEPLOYMENT1 DEPLOYMENT2
aladdin -c CLUSTER -n NAMESPACE environment CONFIGMAP unset --args a b
```
