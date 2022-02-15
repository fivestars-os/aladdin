import subprocess
from aladdin.lib.utils import working_directory


class Git(object):
    SHORT_HASH_SIZE = 10

    @classmethod
    def clone(cls, git_repo, dest_path, depth=1):
        subprocess.check_call(["git", "clone", "--depth", str(depth), git_repo, dest_path])

    @classmethod
    def init_submodules(cls, git_path):
        with working_directory(git_path):
            subprocess.check_call(["git", "submodule", "update", "--init", "--recursive"])

    @classmethod
    def checkout(cls, git_path, ref):
        with working_directory(git_path):
            subprocess.check_call(["git", "checkout", ref])

    @classmethod
    def get_hash(cls):
        return cls._full_hash_to_short_hash(cls.get_full_hash())

    @classmethod
    def get_full_hash(cls):
        cmd = ["git", "rev-parse", "HEAD"]
        return subprocess.check_output(cmd).decode("utf-8").rstrip()

    @classmethod
    def _full_hash_to_short_hash(cls, full_hash):
        return full_hash[: cls.SHORT_HASH_SIZE]

    @classmethod
    def extract_hash(cls, value, git_url):
        """
        Get a hash out of whatever is the value given.
        value: can be a branch name, part of a hash
        """
        if not git_url:
            # There is no way to check anything
            return value

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
                subprocess.check_output(["git", "ls-remote", url, ref], stderr=subprocess.DEVNULL)
                .decode("utf-8")
                .split()
            )
            return output[0] if output else None
        except subprocess.CalledProcessError:
            return None
