# Aladdin Start
Start is one of aladdin's commands used for local development. This command is to be called from within an aladdin-compatible project repo. This command installs a project to your local environment. 
```
usage: aladdin start [-h] [--namespace NAMESPACE] [--dry-run] [--with-mount]
                     [--chart CHART_NAME]...
                     [--force-helm]
                     [--set-override-values SET_OVERRIDE_VALUES [SET_OVERRIDE_VALUES ...]]

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
  --dry-run, -d         Run the helm as test and don't actually run it
  --with-mount, -m      Mount user's host's project repo onto container
  --chart CHART_NAME    Start only these charts (can be specified multiple times)
  --force-helm          Have helm force resource update through
                        delete/recreate if needed
  --set-override-values SET_OVERRIDE_VALUES [SET_OVERRIDE_VALUES ...]
                        override values in the values file. Syntax: --set
                        key1=value1 key2=value2 ...
```
Note that for `--with-mount` to work as expected, you will have to set up the necessary volume and volumeMounts as described in the aladdin demo project [here](https://github.com/fivestars-os/aladdin-demo/blob/master/docs/code_mounting.md).

If the `--chart` option is not provided, all charts defined in the `lamp.json` file will be started.
