import unittest

import mock

from fleeting import utils

class UtilsTests(unittest.TestCase):
    def test_force_preferred_url_scheme_delegates_to_app(self):
        app = mock.MagicMock()
        app.config = dict(PREFERRED_URL_SCHEME='https', SERVER_NAME='f.org')
        start_response = mock.MagicMock()
        environ = {'HTTP_X_FORWARDED_PROTO': 'https',
                   'wsgi.url_scheme': 'http'}
        wsgi_app = app.wsgi_app
        utils.force_preferred_url_scheme(app, 'X-Forwarded-Proto')
        res = app.wsgi_app(environ, start_response)

        self.assertEqual(start_response.call_count, 0)
        self.assertEqual(environ['wsgi.url_scheme'], 'https')
        wsgi_app.assert_called_once_with(environ, start_response)
        self.assertTrue(res is wsgi_app.return_value)

    def test_force_preferred_url_scheme_redirects(self):
        app = mock.MagicMock()
        app.config = dict(PREFERRED_URL_SCHEME='https', SERVER_NAME='f.org')
        start_response = mock.MagicMock()
        environ = dict(SCRIPT_NAME='',
                       PATH_INFO='/goop',
                       QUERY_STRING='ack=foob')
        environ['wsgi.url_scheme'] = 'http'
        wsgi_app = app.wsgi_app
        utils.force_preferred_url_scheme(app)
        res = app.wsgi_app(environ, start_response)

        start_response.assert_called_once_with("302 Found", [
            ("Location", "https://f.org/goop?ack=foob")
        ])
        self.assertEqual(wsgi_app.call_count, 0)
        self.assertEqual(res, ["redirect to https"])

    def test_ensure_env_vars_raises_exception(self):
        msg = 'environment variable QWOP is not defined'
        with self.assertRaisesRegexp(KeyError, msg):
            utils.ensure_env_vars(['QWOP'])
