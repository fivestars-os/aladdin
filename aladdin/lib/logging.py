import logging

import lazy_object_proxy


def getLogger(*args, **kwargs):
    return lazy_object_proxy.Proxy(lambda: logging.getLogger(*args, **kwargs))
