# Aladdin Publish
Publish is one of aladdin's commands used to publish docker images and helm packages so that they can be used to deploy to non local environments. This command is to be called from within an aladdin-compatible project repo.  
This command does the following:
- Clones a git repo of your project into a temp directory on the aladdin docker and checks out your current hash
- Executes your build script, as identified by the project's lamp.json file with HASH={current git hash truncated to 10 characters}
- Publish the docker images built above to ecr
- Create a helm package (contains all values, templates, and chart files), and publish that to s3
- Deletes the temp directory
```
usage: aladdin publish [-h]
                       [--build-only | --build-publish-ecr-only | --publish-helm-only]
                       [--build-local] [--repo REPO] [--git-ref GIT_REF]

optional arguments:
  -h, --help            show this help message and exit
  --build-only          only builds docker images in your minikube env with
                        hash and timestamp as tags
  --build-publish-ecr-only
                        only build and publish docker images to ecr
  --publish-helm-only   only publish helm chart to s3. WARNING: make sure you
                        build and publish the docker images to ecr before
                        deploying
  --build-local         do a local docker build rather than pulling cleanly
                        from git

remote options:
  --repo REPO           which git repo to pull from, which should be used if
                        it differs from chart name
  --git-ref GIT_REF     which commit hash or branch or tag to checkout and
                        publish from
```
- Example: `aladdin publish --build-local`
- Example: `aladdin publish --repo project --git-ref master --publish-helm-only`
