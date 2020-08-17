# Aladdin Undeploy
Undeploy is one of aladdin's commands used to remove projects from non local environments. 
```
usage: aladdin undeploy [-h] [--namespace NAMESPACE] project [--chart CHART_NAME]

positional arguments:
  project               which project to undeploy

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
  --chart CHART_NAME    Which chart to undeploy if your project defines more
                        than a single chart in the lamp.json file, defaults
                        to the project name
```
- Example: `aladdin -c DEV -n test undeploy aladdin-demo`
