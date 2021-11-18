"""
Module to configure environment variables used by Aladdin
"""
import os
import os
import pathlib
import subprocess
from typing import Optional

from jmespath import search

from aladdin import __version__, config
from aladdin.lib import logging

logger = logging.getLogger(__name__)


def configure_env():
    set_repo_path("ALADDIN_PLUGIN_DIR", "plugin_dir", "plugin_repo", required=False)
    manage_software_dependencies: Optional[bool] = search(
        "manage.software_dependencies",
        config.load_user_config()
    )
    os.environ["ALADDIN_MANAGE_SOFTWARE_DEPENDENCIES"] = str(
        # default of True if not specified
        True if manage_software_dependencies is None else manage_software_dependencies
    ).lower()

    # Allow aladdin devs to use a custom aladdin image by setting ALADDIN_IMAGE
    if not (os.getenv("ALADDIN_IMAGE") and config.ALADDIN_DEV):
        # Set ALADDIN_IMAGE from the "aladdin.repo" config (or config.ALADDIN_DOCKER_REPO) and
        # use the aladdin version as the image tag
        os.environ["ALADDIN_IMAGE"] = "{}:{}".format(
            search("aladdin.repo", config.load_config()) or config.ALADDIN_DOCKER_REPO,
            __version__
        )


def set_config_path() -> bool:
    """
    NOTE:
    If this function returns False it will short-circuit execution of
    any aladdin command, so returning False should be preceded by some
    user-friendly error statement about why we're exiting
    """
    return set_repo_path("ALADDIN_CONFIG_DIR", "config_dir", "config_repo", required=True)


def set_repo_path(env_key: str, dir_key: str, repo_key: str, required: bool = False) -> bool:
    """
    Function to set the "dir_key" env var
    Uses git to fetch the latest revision of the repo specified under "repo_key"
    The repo is expected to have a branch or tag that matches the current aladdin version
    """
    if os.getenv(env_key):
        # env value is already set, nothing to do here
        return True

    err_message = (
        f"Unable to find {repo_key}. "
        f"Please use 'aladdin config set {repo_key} "
        "<git@github.com:{git_account}/{repo}.git>' "
        f"to set {repo_key} repo"
    )
    try:
        user_config = config.load_user_config()
    except FileNotFoundError:
        logger.error(err_message)
        return False

    dir_value: str = user_config.get(dir_key)
    repo_value: str = user_config.get(repo_key)
    if not dir_value and not repo_value:
        os.environ[env_key] = ""
        if required:
            logger.error(err_message)
        return not required

    if not repo_value:
        """
        Some users might only have "dir_value" setup because
        "repo_value" was introduced in v1.19.7.14

        This code path makes the version upgrade smooth by automatically setting
        "repo_value" from "dir_value"
        """
        if not os.path.isdir(dir_value):
            logger.error(err_message)
            return False
        try:
            remote = subprocess.run(
                "git remote get-url origin".split(),
                check=True,
                capture_output=True,
                encoding="utf-8",
                cwd=dir_value,
            ).stdout.strip()
        except subprocess.CalledProcessError:
            logger.error(err_message)
            return False
        *_, git_account, repo = remote.split("/")
        repo_value = f"git@github.com:{git_account}/{repo}"
        user_config[repo_key] = repo_value
        config.set_user_config_file(user_config)

    # The config repo is expected to have a branch or tag matching the current aladdin version
    git_commands = [f"git clone -b {__version__} {repo_value} {repo_key}"]
    cwd = pathlib.Path.home() / ".aladdin"
    remote_config_path = cwd / repo_key
    if os.path.isdir(remote_config_path) and os.path.isdir(remote_config_path / ".git"):
        """
        The remote config has already been checked out,
        we update git tags and checkout the latest revision
        """
        cwd = remote_config_path
        git_commands = [
            "git fetch --tags --prune -f",
            f"git checkout {__version__}"
        ]
    for command in git_commands:
        try:
            subprocess.run(
                command.split(),
                check=True,
                encoding="utf-8",
                capture_output=True,
                cwd=str(cwd),
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                "Failed to fetch aladdin %s (%s) from remote: \n%s",
                repo_key,
                repo_value,
                e.stderr.strip() or e.stdout.strip()
            )
            return False

    os.environ[env_key] = str(remote_config_path)

    if config.ALADDIN_DEV and dir_value and os.path.isdir(dir_value):
        """
        Allow aladdin developers to use custom dirs
        """
        os.environ[env_key] = dir_value

    return True
