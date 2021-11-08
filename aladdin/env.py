"""
Module to configure environment variables used by Aladdin
"""
import os
import os
import pathlib
import subprocess

from jmespath import search

from aladdin import __version__, config
from aladdin.lib import logging

logger = logging.getLogger(__name__)


def configure_env():
    os.environ["ALADDIN_PLUGIN_DIR"] = config.load_user_config().get("plugin_dir") or ""
    manage_software_dependencies = search("manage.software_dependencies", config.load_user_config())
    os.environ["ALADDIN_MANAGE_SOFTWARE_DEPENDENCIES"] = (
        # default of True if not specified
        True if manage_software_dependencies is None else manage_software_dependencies
    )

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
    Function to set the "ALADDIN_CONFIG_DIR" env var
    Uses git to fetch the latest revision of the config repo, the repo
    is expected to have a branch or tag that matches the current aladdin version

    NOTE:
    If this function returns False it will short-circuit execution of
    any aladdin command, so returning False should be preceded by some
    user-friendly error statement about why we're exiting
    """
    if os.getenv("ALADDIN_CONFIG_DIR"):
        # Aladdin config is already set, nothing to do here
        return True

    err_message = (
        "Unable to find config repo. "
        "Please use "
        "'aladdin config set config_repo <git@github.com:{git_account}/{repo}.git>' "
        "to set config repo"
    )
    try:
        user_config = config.load_user_config()
    except FileNotFoundError:
        logger.error(err_message)
        return False

    config_dir: str = user_config.get("config_dir")
    config_repo: str = user_config.get("config_repo")
    if not config_dir and not config_repo:
        logger.error(err_message)
        return False

    if not config_repo:
        """
        Some users might only have "config_dir" setup because
        "config_repo" was introduced in v1.19.7.14

        This code path makes the version upgrade smooth by automatically setting
        "config_repo" from "config_dir"
        """
        if not os.path.isdir(config_dir):
            logger.error(err_message)
            return False
        try:
            remote = subprocess.run(
                "git remote get-url origin".split(),
                check=True,
                capture_output=True,
                encoding="utf-8",
                cwd=config_dir,
            ).stdout.strip()
        except subprocess.CalledProcessError:
            logger.error(err_message)
            return False
        *_, git_account, repo = remote.split("/")
        config_repo = f"git@github.com:{git_account}/{repo}"
        user_config["config_repo"] = config_repo
        config.set_user_config_file(user_config)

    # The config repo is expected to have a branch or tag matching the current aladdin version
    git_commands = [f"git clone -b {__version__} {config_repo} remote_config"]
    cwd = pathlib.Path.home() / ".aladdin"
    remote_config_path = cwd / "remote_config"
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
                "Failed to fetch aladdin config (%s) from remote: \n%s",
                config_repo,
                e.stderr.strip() or e.stdout.strip()
            )
            return False

    os.environ["ALADDIN_CONFIG_DIR"] = str(remote_config_path)

    if config.ALADDIN_DEV and config_dir and os.path.isdir(config_dir):
        """
        Allow aladdin developers to use a custom config
        """
        os.environ["ALADDIN_CONFIG_DIR"] = config_dir

    return True
