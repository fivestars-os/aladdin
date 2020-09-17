# Aladdin Restart
Restart is one of aladdin's commands used for local development. This command is to be called from within an aladdin-compatible project repo. This command removes a project from your local environment, and then installs it back.  
```
usage: aladdin restart [-h] [--namespace NAMESPACE] [--with-mount] [--chart CHART_NAME]...

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
  --chart CHART_NAME    Restart only these charts (can be specified multiple times)
  --with-mount, -m      Mount user's host's project repo onto container
```
Note that for `--with-mount` to work as expected, you will have to set up the necessary volume and volumeMounts as described in the aladdin demo project [here](https://github.com/fivestars-os/aladdin-demo/blob/master/docs/code_mounting.md).

If the `--chart` option is not provided, all charts defined in the `lamp.json` file will be
restarted.
