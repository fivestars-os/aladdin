#!/usr/bin/env bash

case "$OSTYPE" in
    cygwin*)
        export_dir="/cygdrive/c/Users"
        mount_dir="/c/Users"
        ;;
    linux*)
        export_dir="/home"
        mount_dir="/home"
        ;;
    *)
        export_dir="/Users"
        mount_dir="/Users"
        ;;
esac

host_ip="192.168.99.1"
read -r -d '' bootlocal <<EOF ||:
#!/bin/sh

sudo systemctl start nfs-client.target
sudo mkdir -p ${mount_dir}
sudo umount ${mount_dir} 2>/dev/null
sudo mount -t nfs -o tcp,rw,hard,noacl,async,nolock ${host_ip}:${export_dir} ${mount_dir}
EOF

echo -e "\\nInstalling persistent start-up script: /var/lib/boot2docker/bootlocal.sh"
minikube ssh -- "echo \"${bootlocal}\" | sudo tee /var/lib/boot2docker/bootlocal.sh >/dev/null"
minikube ssh -- "sudo chmod +x /var/lib/boot2docker/bootlocal.sh && sync"

echo -e "\\nRunning start-up script manually to nfs mount ${mount_dir} directory"
minikube ssh -- "/var/lib/boot2docker/bootlocal.sh"

echo -e "\\nTesting mounts"
echo "============="
minikube ssh -- "mount | grep '${mount_dir}'"

echo -e "\\nTesting directory"
echo "== ${mount_dir} ================="
minikube ssh -- "ls -al ${mount_dir}"
