import json
import os
import pathlib

from aladdin.lib import logging, utils

logger = logging.getLogger(__name__)


PROJECT_ROOT = pathlib.Path(__file__).parent.parent
ALADDIN_DOCKER_REPO = "fivestarsos/aladdin"


def load_cluster_configs():
    return load_config()["clusters"]


def load_cluster_config(cluster):
    return load_config_from_file(
        f'{os.environ["ALADDIN_CONFIG_DIR"]}/{cluster}/config.json'
    )


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
    config_dir = os.getenv("ALADDIN_CONFIG_DIR")
    return load_config_from_file(f"{config_dir}/config.json")


def load_user_config() -> dict:
    path = pathlib.Path.home() / ".aladdin/config/config.json"
    try:
        return load_config_from_file(path)
    except FileNotFoundError:
        logger.warning("User config file not found, creating one with default values")
        default_values = {
            "config_repo": "git@github.com:fivestars/aladdin-config.git",
            "plugin_repo": "git@github.com:fivestars/aladdin-plugins.git",
        }
        set_user_config_file(default_values)
        return default_values


def set_user_config_file(config: dict):
    path = pathlib.Path.home() / ".aladdin/config"
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    with open(path / "config.json", "w") as json_file:
        json.dump(config, json_file, indent=2)


ALADDIN_DEV = utils.strtobool(os.getenv("ALADDIN_DEV", "false"))
