# Aladdin Start
Start is one of aladdin's commands used for local development. This command is to be called from within an aladdin-compatible project repo. This command installs a project to your local environment.
```
usage: aladdin start [-h] [--namespace NAMESPACE] [--dry-run]
                     [--chart CHART_NAME]...
                     [--force-helm]
                     [--set-override-values SET_OVERRIDE_VALUES [SET_OVERRIDE_VALUES ...]]

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
  --dry-run, -d         Run the helm as test and don't actually run it
  --chart CHART_NAME    Start only these charts (can be specified multiple times)
  --force-helm          Have helm force resource update through
                        delete/recreate if needed
  --set-override-values SET_OVERRIDE_VALUES [SET_OVERRIDE_VALUES ...]
                        override values in the values file. Syntax: --set-override-values key1=value1 key2=value2 ...
  --values-file         Override values file to be passed to helm.
                        Syntax: --values-file my-values.yaml (can be specified multiple times)
```

If the `--chart` option is not provided, all charts defined in the `lamp.json` file will be started.
