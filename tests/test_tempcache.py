import unittest

import mock

from fleeting.tempcache import DictTempCache, RedisTempCache

class DictTempCacheTests(unittest.TestCase):
    @mock.patch('time.time')
    def test_cache_expires_items(self, time):
        c = DictTempCache(5)

        time.return_value = 1000
        c['foo'] = dict(hi=1)
        self.assertEqual(c.find('foo'), [{'hi': 1}])

        time.return_value = 1006
        self.assertEqual(c.find('foo'), [])

class RedisTempCacheTests(unittest.TestCase):
    @mock.patch('fleeting.tempcache.redis')
    def test_setitem_works(self, redis):
        r = RedisTempCache(ttl=50, url='redis://foo:6379')
        r['lulz'] = {'hi': 1}
        r.redis.hmset.assert_called_once_with('lulz', {'hi': 1})
        r.redis.expire.assert_called_once_with('lulz', 50)

    @mock.patch('fleeting.tempcache.redis')
    def test_find_works(self, redis):
        r = RedisTempCache(ttl=50, url='redis://foo:6379')
        r.redis.keys.return_value = ['lol']
        r.redis.hgetall.return_value = {'hi': 1}
        self.assertEqual(r.find('lo'), [{'hi': 1}])
        r.redis.keys.assert_called_once_with('lo*')
        r.redis.hgetall.assert_called_once_with('lol')

    @mock.patch('fleeting.tempcache.redis')
    def test_find_removes_empty_dicts(self, redis):
        r = RedisTempCache(ttl=50, url='redis://foo:6379')
        r.redis.keys.return_value = ['lol']
        r.redis.hgetall.return_value = {}
        self.assertEqual(r.find('lo'), [])

    @mock.patch('fleeting.tempcache.redis')
    def test_constructor_works(self, redis):
        r = RedisTempCache(ttl=50, url='redis://foo:6379')
        redis.from_url.assert_called_once_with('redis://foo:6379')
