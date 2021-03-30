import json
import logging
import os
import sys

from pathlib import Path

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


def configure_aladdin_dirs():
    user_config_path = Path.home() / ".aladdin" / "config" / "config.json"
    error_str = (
        "Unable to find config directory. "
        "Please use 'aladdin config set config_dir <config path location>' "
        "to set config directory"
    )

    try:
        user_config = load_config_from_file(user_config_path)
    except FileNotFoundError:
        logging.error(error_str)
        sys.exit(1)

    try:
        os.environ["ALADDIN_CONFIG_DIR"] = user_config["config_dir"]
    except KeyError:
        logging.error(error_str)
        sys.exit(1)

    if not os.path.exists(user_config["config_dir"]):
        logging.error(error_str)
        sys.exit(1)

    os.environ["ALADDIN_PLUGIN_DIR"] = user_config.get("plugin_dir") or ""
