# Aladdin Build
Build is one of aladdin's commands used for local development. This command is to be called from within an aladdin-compatible project repo. This command executes your build script, as identified by the project's lamp.json file. It passes in HASH=local. After this is called, all your internal docker images should be built with the tag local.
```
usage: aladdin build [-h]

optional arguments:
  -h, --help  show this help message and exit
```
