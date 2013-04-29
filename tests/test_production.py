import logging
import unittest

import mock

class ProductionTests(unittest.TestCase):
    @mock.patch('os.environ', {
        'SECRET_KEY': 'bleh secret',
        'SERVER_NAME': 'meh.org',
        'AWS_KEY_NAME': 'ergerg',
        'AWS_SECURITY_GROUP': 'blah',
        'AWS_ACCESS_KEY_ID': 'apoeg',
        'AWS_SECRET_ACCESS_KEY': 'awegaeg'
    })
    @mock.patch('fleeting.app')
    def test_production_works(self, app):
        from fleeting import production

        app.config.update.assert_called_once_with(
            PREFERRED_URL_SCHEME='http',
            SECRET_KEY='bleh secret',
            SERVER_NAME='meh.org'
        )
        self.assertEqual(app.logger.addHandler.call_count, 1)
        app.logger.setLevel.assert_called_once_with(logging.INFO)
        self.assertEqual(app.logger.info.call_count, 1)
