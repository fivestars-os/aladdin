#!/usr/bin/env bash

read -r -d '' bootlocal <<EOF ||:
#!/bin/sh

# The future, that doesn't depend on Cygwin specialization
sudo systemctl start nfs-client.target
sudo mkdir -p /Users
sudo busybox umount /Users 2>/dev/null
sudo busybox mount -t nfs -o tcp,rw,hard,noacl,async,nolock 192.168.99.1:/Users /Users

# Replace the current Cygwin vboxfs mount for now, since I think pathnorm expects to find things here
sudo mkdir -p /c/Users
sudo busybox umount /c/Users 2>/dev/null
sudo busybox mount -t nfs -o tcp,rw,hard,noacl,async,nolock 192.168.99.1:/Users /c/Users
EOF

echo -e "\\nInstalling persistent start-up script: /var/lib/boot2docker/bootlocal.sh"
minikube ssh -- "echo \"${bootlocal}\" | sudo tee /var/lib/boot2docker/bootlocal.sh >/dev/null"
minikube ssh -- "sudo chmod +x /var/lib/boot2docker/bootlocal.sh && sync"

echo -e "\\nRunning start-up script manually to nfs mount /Users directory"
minikube ssh -- "/var/lib/boot2docker/bootlocal.sh"

echo -e "\\nTesting mounts"
echo "============="
minikube ssh -- "mount | grep '/Users'"

echo -e "\\nTesting directories"
echo "== /Users ================="
minikube ssh -- "ls -al /Users"
echo -e "\\n== /c/Users ================="
minikube ssh -- "ls -al /c/Users"
