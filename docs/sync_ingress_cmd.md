# Aladdin Sync_Ingress
Sync-ingress is one of aladdin's commands used to set up ingress rules for Clusters that support ingress. This command interates through all the services, finds the service name, and service port, and creates an ingress rule for each to route traffic.
```
usage: aladdin sync-ingress [-h] [--namespace NAMESPACE]

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
```
- Example: `aladdin -c DEV -n test sync_ingress`
