# Aladdin Restart
Restart is one of aladdin's commands used for local development. This command is to be called from within an aladdin-compatible project repo. This command removes a project from your local environment, and then installs it back.  
```
usage: aladdin restart [-h] [--namespace NAMESPACE] [--chart CHART_NAME]...

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
  --chart CHART_NAME    Restart only these charts (can be specified multiple times)
```

If the `--chart` option is not provided, all charts defined in the `lamp.json` file will be
restarted.
