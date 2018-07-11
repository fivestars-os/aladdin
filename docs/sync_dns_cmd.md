# Aladdin Sync-Dns
Sync-dns is one of aladdin's commands used to map consistent naming endpoints to service LoadBalancers. It does this by creating a cname from {service name}.{namespace}.{cluster dns} to your service ELB. The command will do this for all services in a namespace. 
```
usage: aladdin sync-dns [-h] [--namespace NAMESPACE]

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
```

More info [here](./doc/dns_and_certificate.md)
