import json
import os
import os.path
import subprocess
import sys
from collections import namedtuple

from aladdin.lib import logging

from jmespath import search

DockerContext = namedtuple("DockerContext", ["dockerfile", "context", "name"])
HelmContext = namedtuple("HelmContext", ["chart_home", "values_files", "name"])

logger = logging.getLogger(__name__)


class ProjectConf(object):
    """
    Manage the config of a project through the lamp.json file
    """

    CONFIG_NAME = "lamp.json"

    CONTENT_EXAMPLE = {
        "name": "<project_name>",
        # Commenting this out so that we get the build-components behavior by default,
        # but leaving it here for structural documentation purposes.
        # "build_docker": ["./commands/build.bash"],
        "helm_chart": ["./builds/<project_name>"],
        "docker_images": ["img1", "img2", "img3"],
    }

    @classmethod
    def project_root_locate(cls, path="."):
        cur_path = os.path.abspath(path)
        while cur_path and cur_path != "/":
            lamp_path = os.path.join(cur_path, cls.CONFIG_NAME)
            if os.path.isfile(lamp_path):
                return cur_path, lamp_path
            cur_path, tail = os.path.split(cur_path)
        logger.error(
            "Could not find lamp.json file. Please create one or retry from a project "
            "with a lamp.json file."
        )
        sys.exit()

    def __init__(self, path="."):
        self.path, lamp_path = self.project_root_locate(path)
        # load lamp.json
        with open(lamp_path) as f:
            self.lamp_content = json.load(f)
        self.lamp_checker()

    @property
    def name(self):
        return self.lamp_content["name"]

    @property
    def build_command(self):
        cmd = search("build_docker", self.lamp_content) or ["aladdin", "build-components"]
        return [cmd] if isinstance(cmd, str) else cmd

    def build_docker(self, env=None, build_args=None):
        env = env or {}
        build_args = build_args or []

        command = self.build_command[:]
        command.extend(build_args)

        run_env = os.environ.copy()
        run_env.update(env)
        subprocess.run(command, check=True, cwd=self.path, env=run_env)

    def get_docker_images(self):
        images = search("docker_images", self.lamp_content)
        if isinstance(images, str):
            images = [images]
        return images

    def get_helm_chart_paths(self):
        paths = search("helm_chart", self.lamp_content)
        if isinstance(paths, str):
            paths = [paths]
        return [os.path.join(self.path, path) for path in paths]

    def lamp_checker(self):
        try:
            for key in self.CONTENT_EXAMPLE:
                self.lamp_content[key]
        except KeyError as e:
            logger.error(
                "Could not find '{0}' in your lamp.json file. Please add the field '{0}' "
                "to your lamp.json file and try again.".format(e.args[0])
            )
            sys.exit()
