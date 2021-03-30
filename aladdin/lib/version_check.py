import logging
import os
import sys

from aladdin import __version__
from aladdin.lib import in_aladdin_container, utils
from aladdin.lib.git import Git
from aladdin.config import load_config, PROJECT_ROOT


def check_latest_version():
    if in_aladdin_container():
        return
    config = load_config()
    repo = config["aladdin"]["repo"]
    tag = config["aladdin"]["tag"]
    enforce_version = config["aladdin"].get("enforce_version", False)
    git_url = f"git@github.com:{repo}.git"

    _aladdin_version_check(tag, git_url, enforce_version=enforce_version)
    _config_version_check(tag, git_url, enforce_version=enforce_version)


def _aladdin_version_check(tag, git_url, enforce_version=False):
    live = Git.get_hash_ls_remote(tag, git_url, "--tags")
    current = Git.get_hash_ls_remote(__version__, git_url, "--tags")

    if enforce_version and (not live or not current):
        return logging.warning("Unable to check for latest aladdin version")

    if live != current:
        logging.warning("There is a newer version version of aladdin available")
        if enforce_version:
            logging.error("Please update aladdin to continue")
            sys.exit(1)


def _config_version_check(tag, git_url, enforce_version=False):
    with utils.working_directory(os.environ["ALADDIN_CONFIG_DIR"]):
        current = Git.get_full_hash()
        live = Git.get_hash_show_ref(tag)

    if enforce_version and (not live or not current):
        return logging.warning("Unable to check for latest aladdin config version")

    if live != current:
        logging.warning("There is a newer version version of aladdin config available")
        if enforce_version:
            logging.error("Please update aladdin config to continue")
            sys.exit(1)
