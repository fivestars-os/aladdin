import json
import os
import pathlib
import subprocess
from distutils.util import strtobool

from aladdin.lib import logging
from aladdin.lib.utils import working_directory

logger = logging.getLogger(__name__)


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def load_cluster_configs():
    return load_config()["clusters"]


def load_cluster_config(cluster):
    return load_config_from_file(f'{os.environ["ALADDIN_CONFIG_DIR"]}/{cluster}/config.json')


def load_namespace_override_config(cluster, namespace):
    aladdin_config_dir = os.environ["ALADDIN_CONFIG_DIR"]
    return load_config_from_file(
        f"{aladdin_config_dir}/{cluster}/namespace-overrides/{namespace}/config.json"
    )


def load_publish_configs():
    return load_config()["publish"]


def load_kubernetes_configs():
    return load_config()["kubernetes"]


def load_git_configs():
    return load_config()["git"]


def load_config_from_file(file):
    with open(file) as json_file:
        json_data = json.load(json_file)
    return json_data


def load_config():
    return load_config_from_file(f'{os.environ["ALADDIN_CONFIG_DIR"]}/config.json')


def load_user_config_file() -> dict:
    home = pathlib.Path.home()
    return load_config_from_file(home / ".aladdin/config/config.json")


def set_config_path() -> bool:
    err_message = (
        "Unable to find config directory. "
        "Please use "
        "'aladdin config set config_repo <git@github.com:{git_account}/{repo}.git>' "
        "to set config directory"
    )
    try:
        config = load_user_config_file()
    except FileNotFoundError:
        logger.error(err_message)
        return False

    config_dir: str = config.get("config_dir")
    config_repo: str = config.get("config_repo")
    if not config_dir and not config_repo:
        logger.error(err_message)
        return False

    if not config_repo:
        # backwards compat, auto-set config_repo
        if not os.path.isdir(config_dir):
            logger.error(err_message)
            return False
        with working_directory(config_dir):
            remote = subprocess.run(
                "git remote get-url origin".split(),
                check=True,
                capture_output=True,
                encoding="utf-8"
            ).stdout.strip()
        *_, git_account, repo = remote.split("/")
        config["config_repo"] = f"git@github.com:{git_account}/{repo}.git"

    if strtobool(os.getenv("ALADDIN_DEV", "false")) and config_dir:
        os.environ["ALADDIN_CONFIG_DIR"] = config_dir
        os.environ["ALADDIN_CONFIG_FILE"] = os.path.join(config_dir, "config.json")

    return True
