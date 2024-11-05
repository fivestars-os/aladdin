import datetime
import logging
import pathlib
import time
import functools
import shelve
import shutil
from contextlib import contextmanager, closing
from collections import defaultdict

from aladdin.lib.cluster_rules import ClusterRules

cache_root = pathlib.Path.home() / ".aladdin" / "cache"


@contextmanager
def clear_on_error():
    try:
        yield
    except Exception:
        logging.info("Clearing cache due to error")
        shutil.rmtree(cache_root, ignore_errors=True)
        raise


def certificate_cache(func):
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_path = cache_root / "certificates"
    ttls = defaultdict(
        # the default ttl for existing certificates
        lambda: datetime.timedelta(hours=1),
        # allow checking the status more frequently for new certificates
        {
            "": datetime.timedelta(minutes=1),
            None: datetime.timedelta(minutes=1),
        },
    )

    @functools.wraps(func)
    @clear_on_error()
    def wrapper(certificate_scope):
        if not ClusterRules().certificate_lookup_cache:
            return func(certificate_scope)

        with closing(shelve.open(str(cache_path))) as cache:
            data: dict = cache.get(certificate_scope) or {}

            age = time.time() - data.get("time", 0)
            value = data.get("value")
            ttl = ttls[value]
            if (
                not data
                or age > ttl.total_seconds()
            ):
                value = func(certificate_scope)
                cache[certificate_scope] = {
                    "value": value,
                    "time": time.time(),
                }
            elif value:
                logging.info(
                    "Found CACHED certificate %s for %s",
                    value, certificate_scope
                )
            return value

    return wrapper
