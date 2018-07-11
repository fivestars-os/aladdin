# Aladdin cluster command
The cluster command contains several subcommands to help create, modify, and delete your cluster. 

Before creating your cluster, you will need to configure your DNS using the "Configure DNS" section from this [doc](https://github.com/kubernetes/kops/blob/master/docs/aws.md). Make sure the subdomain you create here matches your cluster's DNS_ZONE in your env.sh file and your root_dns in your config.json file. 

You will now be able to use aladdin to create your cluster. 

## Sample cluster creation steps
```
aladdin -c <CLUSTER NAME> cluster create-config # Create the kops cluster resource
aladdin -c <CLUSTER NAME> cluster export-config # Export the cluster resource file to your aladdin config folder, for you to make any necessary modifcations, and for you to source control your cluster configuration
aladdin -c <CLUSTER NAME> cluster import-config # Update your kops resources with your modifications if you made any
aladdin -c <CLUSTER NAME> cluster create-at-aws # Actually create the cluster on aws (this takes around 10 minutes)
aladdin -c <CLUSTER NAME> cluster init # Install all projects from your specified by config.json's cluster_init field
```

Note: aladdin doesn't currently support creating instance groups. You will need to manually do that by dropping into aladdin bash:
```
aladdin -c <CLUSTER NAME> bash
kops create ig {ig name} {flags}
```
You can then export these to make necessary modifications, and then import your modifications. 

Then, when the time comes, to delete your cluster:
```
aladdin -c <CLUSTER NAME> cluster delete
```
## Other aladdin cluster commands
`aladdin -c <CLUSTER NAME> cluster backup` create a folder called `backup` in your config folder, cluster subdirectory with all your k8s resources, separated on the namespace level.  
`aladdin -c <CLUSTER NAME> cluster populate` use the `backup` folder in your config folder, cluster subdirectory, to populate your cluster with all the k8s resources.  
Note: these above two commands are useful when upgrading a kubernetes cluster, by backing up the old cluster, moving the backup folder to your new cluster's config folder, and then populating the cluster. 

`aladdin -c <CLUSTER NAME> cluster update-at-aws` update cluster configuration without restarting cluster nodes
`aladdin -c <CLUSTER NAME> cluster rolling-update-at-aws` update cluster configuration by restarting cluster nodes
`aladdin -c <CLUSTER NAME> cluster view-config` display cluster info and configuration

## Usage
```
usage: aladdin [-h] [--cluster CLUSTER] [--namespace NAMESPACE] [--admin]
               [--init] [--dev] cluster
               {backup,create-at-aws,create-config,delete,export-config,import-config,init,populate,rolling-update-at-aws,update-at-aws,view-config}
               ...

Manage kubernetes clusters

positional arguments:
  {backup,create-at-aws,create-config,delete,export-config,import-config,init,populate,rolling-update-at-aws,update-at-aws,view-config}
                        cluster subcommands
    backup              export all k8s resources for each namespace to minikube/<namespace>.yaml for later repopulation
    create-at-aws       create cluster minikube from kops configuration
    create-config       import kops configuration for cluster minikube based on minikube environment file
    delete              delete cluster minikube
    export-config       export kops configuration for cluster minikube to host machine
    import-config       update kops cluster minikube state with host machine cluster files
    init                deploy all cluster_init projects as specified by your minikube config.json file
    populate            populate a cluster using the minikube/<namespace>.yaml files generated from cluster backup
    rolling-update-at-aws
                        update cluster configuration by restarting cluster nodes
    update-at-aws       update cluster configuration without restarting cluster nodes
    view-config         display cluster info and configuration

optional arguments:
  -h, --help            show this help message and exit
  --cluster CLUSTER, -c CLUSTER
                        cluster dns, defaults to minikube current : [minikube]
  --namespace NAMESPACE, -n NAMESPACE
                        namespace name, defaults to default current : [default]
  --init                force the initialization steps (dl latest docker, aws auth, etc...)
  --dev                 mount host's aladdin directory onto aladdin container
```
