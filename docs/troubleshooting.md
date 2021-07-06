# Troubleshooting
You may want to first try:
- Rerunning your aladdin command with `--init` flag
- Restarting your LOCAL cluster via `k3d cluster delete LOCAL && aladdin --init` and then rerunning your command
## Specific Issues
### InvalidSignatureException
Fix this by restarting your LOCAL cluster via `k3d cluster delete LOCAL && aladdin --init` and then rerunning your command
### Problems with git processing during aladdin deploy or publish
If your error is something like this:
```
Cloning into '/tmp/tmp7sihubxt'...
Bad owner or permissions on /root/.ssh/config
fatal: Could not read from remote repository.
 
Please make sure you have the correct access rights
and the repository exists.
``` 
try: `chmod 6000 ~/.ssh/config` before rerunning your command
### Error: could not find tiller
Rerun your aladdin command with `--init` flag to initialize tiller via helm
### Error: could not find a ready tiller pod
Tiller is still initializing. Wait a minute, and then rerun your aladdin command.
### Aws parsing issues
Make sure your ~/.aws/credentials file is of this format:
```
[{profile-name-1}]
aws_access_key_id =  {your profile-name-1 access key id}
aws_secret_access_key =  {your profile-name-1 secret access key}
[{profile-name-2}]
aws_access_key_id =  {your profile-name-2 access key id}
aws_secret_access_key =  {your profile-name-2 secret access key}
```
and make sure your ~/.aws/config file is of this format:
```
[profile {profile-name-1}]
output = json
region = {your profile-name-1 aws region}
[profile {profile-name-2}]
output = json
region = {your profile-name-2 aws region}
```
