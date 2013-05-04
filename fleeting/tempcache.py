import time
from copy import deepcopy
from threading import Lock

import redis

class DictTempCache(object):
    def __init__(self, ttl):
        self.__cache = {}
        self.ttl = ttl
        self.lock = Lock()

    def __cleanup(self):
        now = time.time()
        for key in self.__cache.keys():
            if now >= self.__cache[key]['expiry']:
                del self.__cache[key]

    def __setitem__(self, key, value):
        with self.lock:
            self.__cleanup()
            self.__cache[key] = dict(value=deepcopy(value),
                                     expiry=time.time() + self.ttl)

    def find(self, prefix):
        with self.lock:
            self.__cleanup()
            return [deepcopy(self.__cache[key]['value'])
                    for key in self.__cache
                    if key.startswith(prefix)]

class RedisTempCache(object):
    def __init__(self, ttl, url='redis://localhost:6379'):
        self.ttl = ttl
        self.redis = redis.from_url(url)

    def __setitem__(self, key, value):
        self.redis.hmset(key, value)
        self.redis.expire(key, self.ttl)

    def find(self, prefix):
        items = [self.redis.hgetall(key)
                 for key in self.redis.keys('%s*' % prefix)]
        return [item for item in items if item]
