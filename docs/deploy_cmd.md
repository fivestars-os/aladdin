# Aladdin Deploy
Deploy is one of aladdin's commands used for to deploy projects to non local environments. This command pulls a project's helm package from s3, sets the container images to the full ecr path with git ref as tag, and installs/upgrades the previously deployed project. This command can check the deployed hash against a given branch (set in your aladdin config) unless the `--force` option is supplied.  
```
usage: aladdin deploy [-h] [--namespace NAMESPACE] [--dry-run] [--force]
                      [--repo REPO]
                      [--set-override-values SET_OVERRIDE_VALUES [SET_OVERRIDE_VALUES ...]]
                      project git_ref

positional arguments:
  project               which project to deploy
  git_ref               which git hash or tag or branch to deploy

optional arguments:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current :
                        [default]
  --dry-run, -d         Run the helm as test and don't actually run it
  --force, -f           Skip git branch verification if check_branch is
                        enabled on the cluster
  --force-helm          Have helm force resource update through
                        delete/recreate if needed
  --repo REPO           which git repo to pull from, which should be used if
                        it differs from chart name
  --set-override-values SET_OVERRIDE_VALUES [SET_OVERRIDE_VALUES ...]
                        override values in the values file. Syntax: --set
                        key1=value1 key2=value2 ...
```
- Example: `aladdin -c DEV -n test deploy aladdin-demo 8d2j8f30bd`
- Example: `aladdin -c PROD deploy aladdin-demo master`
- Example: `aladdin -c DEV -n test deploy aladdin-demo 5a5e59b2f6 --set-override-values replicas=3 resources.cpu.request.enable=true`

Note: Although this command is primarily used for non local environments, you can still use it in minikube rather than using `aladdin start`. The benefit of this is that you are not required to have the project pulled locally. The cons of this is that you have to get the githash you want to deploy, and you cannot mount your host code in this method.

Also note: Aladdin deploy will also request a certificate arn for `*.{namespace}.{cluster dns}` or `*.{service_dns_suffix}` if you have supplied `service_dns_suffix` in your config. It will use helm to pass in `--set service.certificateArn={certificate arn}` once the certificate is issued. Since the certificate validation happens asynchronously, it may not be applied the first time you deploy. However, once it is issued, if you have these lines in your k8s service yaml file:
```
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: {{.Values.service.certificateArn | quote}}
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: http
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
```
you will be able to enable ssl on your service by redeploying your project.
