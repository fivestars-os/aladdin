# Aladdin

## What is Aladdin?

Inspired by the Genie of the Lamp, Aladdin is a command line tool built by Fivestars to simplify kubernetes operations for clusters management and application development. We have done this by combining several command line tools including kops, minikube, docker, kubectl, helm, awscli, and git.

Use aladdin to:
- Create and manage an aws kubernetes cluster
- Upgrade your aws kubernetes cluster
- Run and deploy your organization's applications across different environments (including locally) with environment specific configuration
- Run operation-type commands against your application (e.g. putting your application into maintenance mode)

## How does Aladdin work?
Aladdin has two main components. One component runs on your host machine, and one component runs in a docker container, started by the first component.

The host component is responsible for:
- Parsing command line options
- Running any commands to be executed on the host machine
- Checking and warning about any missing dependencies or installing the dependency in `~/.aladdin/bin` if possible
- Starting minikube
- Pulling the aladdin image
- Running the aladdin docker container (the container component) within minikube

The container component is responsible for
- Running commands to manage your aws kubernetes cluster
- Running commands to deploy and manipulate your applications on your kubernetes cluster

### Script Diagram/Architecture

<img src="diagram/diagram.png" width="600"/>

## Installing Aladdin

To set up, just clone the Aladdin GitHub repository to get started:

    $ git clone git@github.com:fivestars-os/aladdin.git
    $ cd aladdin
    $ scripts/infra_k8s_check.sh

The `infra_k8s_check.sh` script checks to see if all of aladdin's dependencies are installed. Depending on the dependency, it will warn if it is missing or install it in `~/.aladdin/bin` if possible. This script is also run every time you run aladdin.

You may want to add aladdin to your path:

    $ eval $(./aladdin.sh env)

You may also want to add `~/.aladdin/bin` to your path:

    $ export PATH=$PATH:~/.aladdin/bin

You can add these two commands to your profile file if desired.

You will now need to [create your aladdin configuration](./docs/create_aladdin_configuration.md), and link that to aladdin.

    $ aladdin config set config_dir /path/to/aladdin/configuration

### VM Configuration
Currently, two parameters are configurable:
 * memory: By default, we create a minikube vm with 4096MB (4GB) of memory.  To change the size of the vm we create to e.g. 8GB, you may run:
```
aladdin config set minikube.memory 8192
```
 * vm\_driver: By default, we use the 'virtualbox' virtualization backend.  Currently, we support only this and the `none` backend, which runs containers directly on the underlying OS without virtualization (only supported on
   linux).  If your host is running linux, and you wish to use the 'none' backend (and avoid running in a VM), you may run,
```
aladdin config set minikube.vm_driver none
```

Note that these commands only take effect when the minikube cluster is first set up --- in order for them to take effect, you will need to first delete your existing minikube cluster (if present) and then (re-)run `aladdin --init`.

### NFS mounts

Aladdin uses minikube for local development which is a VirtualBox-based VM. Internally it mounts your `/Users` (or `/cygdrive/c/Users` for Cygwin users) directory to the root of the minikube filesystem. We have discovered that the `vboxsf` mounts are not as performant as NFS mounts and furthermore are not as reliable when it comes to detecting file changes made from the host. To address this, we replace the `vboxsf` mounts within minikube with NFS mounts. However, this requires a bit of manual setup on the host machine before it will take effect.

#### NFS Host Setup

1. Install an NFS service on your host
    1. **macOS** You should already have it available.
    1. **Windows** You should install Cygwin and the `unfsd` package
        * Take care when configuring the `unfsd` package as it can inadvertently remove login capabilities for your active user account.
        * Be sure to add firewall exceptions for the installed services (/usr/sbin/unfsd & /usr/sbin/rpcbind).
1. Add entries to your `/etc/exports` file
    1. **macOS**
    ```
    echo "/Users -alldirs -mapall="$(id -u)":"$(id -g)" $(minikube ip)" | sudo tee -a /etc/exports
    ```
    1. **Windows**
    ```
    # Ensure you have a line for "minikube" in your /etc/hosts file.
    cat /etc/hosts

    # If not, add it when you get minikube up and running.
    echo "$(minikube ip) minikube" >> /etc/hosts

    # Export this /Users directory as an NFS share.
    echo "/cygdrive/c/Users    minikube(rw,all_squash,anonuid=$(id -u),anongid=$(id -g))" >> /etc/exports

    # Restart the unfsd service through the Windows Service GUI now.
    ```

## Creating and managing an aws kubernetes cluster
This is all encapsulated in the [aladdin cluster command](./docs/cluster_cmd.md)

## Integrating your application with aladdin
There is some plumbing you need to add to your application source code in order to get it to integrate with aladdin. We have created an aladdin-demo project that walks you through these steps. It also includes what we think of as "best practices" in developing applications on kubernetes. You can also use this project to verify your aladdin installation is working correctly. Please refer to the aladdin demo instructions [here](https://github.com/fivestars-os/aladdin-demo).

## Project development
We have several aladdin commands used for development and deployment. Note that are you implicitly or explicitly calling these commands with respect to a namespace and cluster (through the -n and -c flags).
### Aladdin local dev commands
- [aladdin build](./docs/build_cmd.md) used to build a project's docker images locally with the local tag
- [aladdin start](./docs/start_cmd.md) used to install or update a project locally
- [aladdin stop](./docs/stop_cmd.md) used to uninstall a project locally
- [aladdin restart](./docs/restart_cmd.md) used to uninstall and reinstall a project locally
- [aladdin publish](./docs/publish_cmd.md) used to publish your project's docker images to your ecr and publish your helm packages to s3 to be used to deploy to non local environments

### Aladdin non local commands
- [aladdin deploy](./docs/deploy_cmd.md) used to deploy to a remote, non-local cluster
- [aladdin undeploy](./docs/undeploy_cmd.md) used to remove a project from a remote, non-local cluster
- [aladdin rollback](./docs/rollback_cmd.md) used to go back to a previous deployment

### Aladdin local and non local commands
- [aladdin cmd](./docs/cmd_cmd.md) used to issue commands against a project (e.g. putting a project into maintenance)
- [aladdin environment](./docs/environment_cmd.md) used to get or maniuplate config maps
- [aladdin refresh](./docs/refresh_cmd.md) issue a no-op deployment, which is useful to restart all pods in a deployment
- [aladdin scale](./docs/scale_cmd.md) used to change the number of replicas for a deployment
- [aladdin connect](./docs/connect_cmd.md) used to connect to a container's shell

## Sample development workflow
- `git clone git@github.com:{git account name}/{project repo name}.git`
- `cd {project repo name}`
- `git checkout -b {feature branch}`
- `aladdin build`
- `aladdin start --with-mount`
- do some development
- commit code and push to remote
- `aladdin publish` (publishes current hash, remember what that hash is)
- `aladdin -c {remote integration cluster} -n {your personal namespace} deploy {project-repo-name} {hash from previous step}` - Your app will be running at `{service-name}.{namespace}.{cluster root dns}` or `{service-name}.{service_dns_suffix}` if you specified a service_dns_suffix
- Test to make sure everything is working right
- Merge your feature branch to master
- Pull latest master, and run `aladdin publish`. Remeber the hash it is building off of.
- Deploy to your production cluster `aladdin -c {production cluster} deploy {project-repo-name} {hash from previous step}`
- Your app will be running at `{service-name}.{namespace}.{cluster root dns}` or `{service-name}.{service_dns_suffix}` if you specified a service_dns_suffix
- Rollback if necessary with `aladdin -c {production cluster} rollback {project-repo-name}`

## Other useful aladdin commands
- `aladdin bash` drop into the aladdin container bash, with your context set to your current cluster and namespace, with all container commands aliased.
- `aladdin clean` remove all stopped and unused docker images.
- `aladdin config` maniuplate various aladdin config.
- `aladdin create-namespace` create the namespace you pass in.
- `aladdin delete-namespace` delete the namespace you pass in _after_ removing all the helm packages on that namespace.
- `aladdin get-dashboard-url` will output the url of your cluster's dashboard assuming it is installed.
- `aladdin get-minikube-endpoints` show endpoints for all minikube services, essentially wrapping `minikube service list`.
- `aladdin host` give instructions to update your local /etc/hosts file for minikube ingress compatibility.
- For a complete list of aladdin commands, run `aladdin -h`.

## Optional arguments to aladdin
- `-h/--help` show help.
- `-c/--cluster` which cluster to connect to, defaults to `minikube`.
- `-n/--namespace` which namespace to connect to, defaults to `default`.
- `--init` force initialization logic (i.e. pull latest aladdin image, test aws config, initialize helm, etc...). This is forced every hour for each cluster/namespace combo.
- `--dev` mount host's aladdin directory onto aladdin container. Useful when developing aladdin.
- `--skip-prompts` skip any confirmation messages during aladdin execution. Useful when automating commands.
- `--non-terminal` run aladdin container without tty.

## Running several aladdin commands in the same cluster/namespace combo
Aladdin supports running several commands in the same cluster/namespace combo without having to "reinitialize" aladdin. To do this, go into `aladdin bash`. Then all the container commands will be aliased to be run without prefixing aladdin.
Example:
```
$ aladdin bash
     . . .
Launching bash shell. Press CTRL+D to come back to this menu.
This bash contain a lot of functions to help
Don't forget to checkout scripts/bash_profile.bash in aladdin
minikube:default> build
Building aladdin-demo docker image (~30 seconds)
docker build -t aladdin-demo:local -f app/Dockerfile .
Sending build context to Docker daemon  28.16kB
     . . .
Successfully tagged aladdin-demo-commands:local
minikube:default> start --with-mount
INFO:Found cluster values file
     . . .
minikube:default> refresh aladdin-demo-server
INFO:Refreshing deployment aladdin-demo-server
minikube:default>
```

## Tests
Right now we have some e2e tests for aladdin that come in two flavors: `aladdin test-local` and `aladdin test-remote`. These tests require some configuration, an example of which can be found [here](https://github.com/fivestars-os/aladdin-e2e-tests-config). You will need to make some modifications to this config so it has access to create and destroy a temporary cluster on your aws account. Then:
```
aladdin config set config_dir /path/to/your/e2e/tests/config
aladdin test-local
aladdin test-remote
```
Adding tests is a great way to get started with contributing to aladdin!

## Plugins
Aladdin also has the ability to invoke user plugins. The directory structure must be as follows:
```
plugins-folder-name/
  container/
    plugin-name-1/
      plugin-name-1 (must match directory name)
      plugin-name-1-helper-1
      plugin-name-1-helper-2
    plugin-name-2/
      plugin-name-2 (must match directory name)
    plugin-name-3/
      plugin-name-3 (must match directory name)
      plugin-name-3-helper-1
  host/
    plugin-name-4/
      plugin-name-4 (must match directory name)
      plugin-name-4-helper-1
      plugin-name-4-helper-2
    plugin-name-5/
      plugin-name-5 (must match directory name)
    plugin-name-6/
      plugin-name-6 (must match directory name)
      plugin-name-6-helper-1
```
Then:
```
aladdin config set plugin_dir /path/to/plugins-folder-name`
aladdin plugin-name-2 # Execute plugin 2
aladdin plugin-name-5 # Execute plugin 5
```
Plugins are useful for adding lightweight helper functions that are _personally_ useful. If you can't fit it into this model, consider extending aladdin by creating a custom aladdin docker image, and updating your config to use that image. If you think your plugin is _universally_ useful, consider creating a PR and adding it to aladdin itself.

## Other Features
### Ingress per namespace feature
Aladdin supports an ingress per namespace feature. This is off by default. We recommend using this for your shared development cluster to keep the number of elbs low. To turn this on, you'll need to do the following steps:
- Pull [our open sourced ingress-nginx](https://github.com/fivestars-os/ingress-nginx) and alter the values files to your organization's needs. Then, use aladdin to publish it to your ecr.
- Add this to your cluster's config.json file:
```
    "namespace_init": [
        {"project": "ingress-nginx", "ref": "<your published ref>"}
    ],
    "ingress_info": {
        "use_ingress_per_namespace": true,
        "ingress_controller_service_name": "ingress-nginx",
        "ingress_name": "ingress"
    }
```
The "namespace_init" field tells aladdin to install the ingress-nginx project on namespace creation. This will be needed on remote clusters, but not on minikube, since we enable the ingress minikube addon.
The "ingress_info" field tells aladdin how to sync your ingress. Services installed on a cluster with this feature will want to have their service type set to `NodePort` rather than `LoadBalancer`. This is most easily done by setting it in the values field in your cluster's config.json file, i.e. adding this:
```
    "values": {
        "service.publicServiceType": "NodePort",
    }
```
and then referencing `{{ service.publicServiceType }}` in your service yaml file.

## Troubleshooting
[Here](./docs/troubleshooting.md) is a list of common issues and their solutions.
