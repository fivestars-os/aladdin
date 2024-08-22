import logging
import os
import subprocess
import tempfile
import sys
from contextlib import contextmanager, suppress

from aladdin.lib.utils import working_directory
from aladdin.lib.helm_rules import HelmRules
from aladdin.config import load_git_configs


class Git:
    SHORT_HASH_SIZE = 10

    @classmethod
    def clone(cls, git_repo, dest_path):
        subprocess.check_call(["git", "clone", git_repo, dest_path])

    @classmethod
    def init_submodules(cls, git_path):
        with working_directory(git_path):
            subprocess.check_call(["git", "submodule", "update", "--init", "--recursive"])

    @classmethod
    def checkout(cls, git_path, ref):
        with working_directory(git_path):
            subprocess.check_call(["git", "checkout", ref])

    @classmethod
    def get_repo_name(cls):
        origin = subprocess.check_output(["git", "remote", "get-url", "origin"], encoding="utf-8").strip()
        slug = os.path.basename(origin)
        return slug[:-4] if slug.endswith(".git") else slug

    @classmethod
    def get_hash(cls):
        return cls._full_hash_to_short_hash(cls.get_full_hash())

    @classmethod
    def get_full_hash(cls):
        return subprocess.check_output(["git", "rev-parse", "HEAD"], encoding="utf-8").rstrip()

    @classmethod
    def clean_working_tree(cls):
        try:
            subprocess.check_output(["git", "diff", "--exit-code", "--quiet"], encoding="utf-8")
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    @classmethod
    def get_base_directory(cls):
        return subprocess.check_output(["git", "rev-parse", "--show-toplevel"], encoding="utf-8").strip()

    @classmethod
    def _full_hash_to_short_hash(cls, full_hash):
        return full_hash[: cls.SHORT_HASH_SIZE]

    @classmethod
    def extract_hash(cls, value, git_url=None):
        """
        Get a hash out of whatever is the value given.
        value: can be a branch name, part of a hash
        """
        if not git_url:
            # There is no way to check anything
            return cls._full_hash_to_short_hash(str(value))

        ls_remote_res = cls._get_hash_ls_remote(value, git_url)
        if ls_remote_res:
            return cls._full_hash_to_short_hash(str(ls_remote_res))

        # Default is to return the value, truncated to the size of a hash
        return cls._full_hash_to_short_hash(value)

    @classmethod
    def _get_hash_ls_remote(cls, ref, url):
        """
        This get the info from remote without having to download project/data
        :param ref:
        :param url:
        """
        try:
            output = (
                subprocess.check_output(
                    ["git", "ls-remote", url, ref],
                    stderr=subprocess.DEVNULL,
                    encoding="utf-8",
                )
                .split()
            )
            return output[0] if output else None
        except subprocess.CalledProcessError:
            return None


@contextmanager
def clone_and_checkout(githash, repo_name=None):
    current_hash = None
    current_repo = None
    with suppress(subprocess.CalledProcessError):
        current_repo = Git.get_repo_name()
        current_hash = Git.get_hash()

    if (
        current_hash and
        current_repo and
        (current_repo == repo_name or not repo_name) and
        current_hash == githash and
        (Git.clean_working_tree() or HelmRules.debug)
    ):
        yield Git.get_base_directory()
        return

    if not repo_name:
        logging.error(f"No repo found or specified")
        return sys.exit(1)

    git_account = load_git_configs()["account"]
    git_url = f"git@github.com:{git_account}/{repo_name}.git"

    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            Git.clone(git_url, tmpdirname)
        except subprocess.CalledProcessError:
            logging.warn(f"Could not clone repo {git_url}. Does it exist?")
            return sys.exit(1)
        try:
            Git.checkout(tmpdirname, githash)
        except subprocess.CalledProcessError:
            logging.warn(
                f"Could not checkout to ref '{githash}' in repo {git_url}. Have you pushed it to remote?"
            )
            return sys.exit(1)
        yield tmpdirname
