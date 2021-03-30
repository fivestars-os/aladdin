import os
from distutils.util import strtobool


def in_aladdin_container():
    return bool(strtobool(os.getenv("ALADDIN_CONTAINER", "false")))
