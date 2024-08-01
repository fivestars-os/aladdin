import contextlib
import os
from typing import TypeVar


@contextlib.contextmanager
def working_directory(path):
    """A context manager which changes the working directory to the given
    path, and then changes it back to its previous value on exit.

    """
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


Singleton = TypeVar("Singleton")


def singleton(wrapped: Singleton) -> Singleton:
    """Replace class with subclass whose constructor always returns the same instance"""

    class wrapper(wrapped):
        __instance = None
        __initialized = False

        def __new__(cls, *args, **kwargs):
            # Only call the real constructor once.
            if cls.__instance is None:
                cls.__instance = super(wrapper, cls).__new__(cls)
            return cls.__instance

        def __init__(self, *args, **kwargs):
            # Only initialize the instance once.
            if not self.__initialized:
                super(wrapper, self).__init__(*args, **kwargs)
            self.__initialized = True

        @classmethod
        def singleton_reset_(cls):
            cls.__instance = None
            cls.__initialized = False

    # Make sure the replacement class looks like the class it's replacing
    wrapper.__module__ = wrapped.__module__
    wrapper.__name__ = wrapped.__name__
    if hasattr(wrapped, "__qualname__"):
        wrapper.__qualname__ = wrapped.__qualname__

    return wrapper


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False

    raise ValueError("invalid truth value %r" % (val,))
