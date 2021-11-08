import os
import os
import pathlib
import subprocess

from jmespath import search

from aladdin import __version__, config
from aladdin.lib import logging
from aladdin.lib.utils import working_directory

logger = logging.getLogger(__name__)


def configure_env():
    os.environ["ALADDIN_PLUGIN_DIR"] = config.load_user_config().get("plugin_dir") or ""
    manage_software_dependencies = search("manage.software_dependencies", config.load_user_config())
    os.environ["ALADDIN_MANAGE_SOFTWARE_DEPENDENCIES"] = (
        # default of True if not specified
        True if manage_software_dependencies is None else manage_software_dependencies
    )
    if not os.getenv("ALADDIN_IMAGE") or not config.ALADDIN_DEV:
        os.environ["ALADDIN_IMAGE"] = "{}:{}".format(
            search("aladdin.repo", config.load_config()) or config.ALADDIN_DOCKER_REPO,
            __version__
        )


def set_config_path() -> bool:
    """
    Function to set the "ALADDIN_CONFIG_DIR" env var
    Uses git to fetch the latest revision of the config repo

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
        # try to auto-set config_repo
        if not os.path.isdir(config_dir):
            logger.error(err_message)
            return False
        with working_directory(config_dir):
            try:
                remote = subprocess.run(
                    "git remote get-url origin".split(),
                    check=True,
                    capture_output=True,
                    encoding="utf-8"
                ).stdout.strip()
            except subprocess.CalledProcessError:
                logger.error(err_message)
                return False
        *_, git_account, repo = remote.split("/")
        config_repo = f"git@github.com:{git_account}/{repo}"
        user_config["config_repo"] = config_repo
        config.set_user_config_file(user_config)

    remote_config_path = pathlib.Path.home() / ".aladdin/remote_config"
    commands = [f"git clone -b {__version__} {config_repo} remote_config"]
    cwd = pathlib.Path.home() / ".aladdin"
    if os.path.isdir(remote_config_path) and os.path.isdir(remote_config_path / ".git"):
        cwd = remote_config_path
        commands = [
            "git fetch --tags --prune -f",
            f"git checkout {__version__}"
        ]
    with working_directory(cwd):
        for command in commands:
            try:
                subprocess.run(
                    command.split(),
                    check=True,
                    encoding="utf-8",
                    capture_output=True
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
