# Aladdin Rollback
Rollback is one of aladdin's commands used for to rollback deployments in non local environments. This command creates a new deployment revision which matches `--num-versions` versions previous to the current revision. 
```
usage: aladdin rollback [-h] [--namespace NAMESPACE]
                        [--num-versions NUM_VERSIONS]
                        project

positional arguments:
  project               which project to undeploy

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
  --num-versions NUM_VERSIONS
                        how many versions to rollback, defaults to 1
```
- Example: `aladdin -c DEV -n test rollback aladdin-demo --num-versions 2` 

Note: that since rollback creates a new revision, calling rollback twice with --num-versions set to 1 (by default) will get you where you started rather than 2 revisions previous.
