# Aladdin Cmd
Cmd is one of aladdin's commands used to issue commands against a project. This command finds the commands app pod if it exists, and issues a kubectl exec command against it and passes the rest of the command line arguments to the exec command.
```
usage: aladdin cmd [-h] [--namespace NAMESPACE] app_name ...

positional arguments:
  app_name              app to run commands against
  comm_args             command and its args

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
```
- Example: `aladdin cmd aladdin-demo status`

## Commands pod architecture
Information on how the commands pod should be set up to integrate correctly can be found [here](https://github.com/fivestars-os/aladdin-demo/blob/master/docs/commands_containers.md)
