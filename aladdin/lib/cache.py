import datetime
import logging
import pathlib
import time
import functools
import shelve
from collections import defaultdict


def certificate_cache(func):
    cache_path = pathlib.Path.home() / ".aladdin" / "cache" / "certificates"
    ttls = defaultdict(
        # the default ttl for existing certificates is 1 hour
        lambda: datetime.timedelta(hours=1),
        # for new certificates, we want to check the status more frequently
        {
            "": datetime.timedelta(minutes=5),
            None: datetime.timedelta(minutes=5),
        }
    )

    @functools.wraps(func)
    def wrapper(certificate_scope):
        cache = shelve.open(cache_path)
        data: dict = cache.get(certificate_scope) or {}

        age = time.time() - data.get("time", 0)
        value = data.get("value")
        ttl = ttls[value]
        if not data or age > ttl.total_seconds():
            value = func(certificate_scope)
            cache[certificate_scope] = {
                "value": value,
                "time": time.time(),
            }
            cache.close()
        else:
            logging.info("Found CACHED certificate %s for %s", value, certificate_scope)
        return value

    return wrapper
