import importlib.metadata

__version__ = importlib.metadata.version("aladdin")
VERSION = tuple(__version__.split("."))
