# Aladdin Scale
Scale is one of aladdin's commands used to scale a deployment up or down, i.e. change how many pods you are running.   
```
usage: aladdin scale [-h] [--namespace NAMESPACE] deployment replicas

positional arguments:
  deployment            which deployment to scale
  replicas              how many replicas to scale to

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
```
- Example: `aladdin scale aladdin-demo-server 4`
