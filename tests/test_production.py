import logging
import unittest

import mock

from fleeting import project

class ProductionTests(unittest.TestCase):
    @mock.patch('fleeting.tempcache.RedisTempCache')
    @mock.patch('os.environ', {
        'SECRET_KEY': 'bleh secret',
        'SERVER_NAME': 'meh.org',
        'AWS_KEY_NAME': 'ergerg',
        'AWS_SECURITY_GROUP': 'blah',
        'AWS_ACCESS_KEY_ID': 'apoeg',
        'AWS_SECRET_ACCESS_KEY': 'awegaeg',
        'REDISTOGO_URL': 'redis://redis.me:6379'
    })
    @mock.patch('fleeting.app')
    def test_production_works(self, app, RedisTempCache):
        from fleeting import production

        app.config.update.assert_called_once_with(
            PREFERRED_URL_SCHEME='http',
            SECRET_KEY='bleh secret',
            SERVER_NAME='meh.org'
        )
        self.assertEqual(app.logger.addHandler.call_count, 1)
        app.logger.setLevel.assert_called_once_with(logging.INFO)
        self.assertEqual(app.logger.info.call_count, 2)
        RedisTempCache.assert_called_once_with(
            3600,
            url='redis://redis.me:6379'
        )
        self.assertTrue(project.cache is RedisTempCache.return_value)
