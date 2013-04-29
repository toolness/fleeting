import unittest

import browserid
from flask import session
import mock

import fleeting
import fleeting.csrf

fleeting.app.config.update(
    DEBUG=True,
    TESTING=True,
    SECRET_KEY='testing',
    SERVER_NAME='foo.org'
)

fleeting.csrf.uuid4 = lambda: 'csrf!'

def fake_verify(assertion, origin):
    if origin != 'http://foo.org':
        raise Exception('bad origin: %s' % origin)
    return {'email': assertion}

browserid.verify = fake_verify

class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = fleeting.app.test_client()
 
    def test_csrf_works(self):
        rv = self.app.post('/logout')
        self.assertEqual(rv.status, '400 BAD REQUEST')

    def test_login_and_logout_work(self):
        with fleeting.app.test_client() as c:
            # Set the CSRF token.
            c.get('/')
            self.assertTrue('email' not in session)

            # Login.
            rv = c.post('/login', data=dict(
                assertion='foo@bar.org',
                _csrf_token='csrf!'
            ))
            self.assertEqual(rv.status, '200 OK')
            self.assertEqual(rv.data, 'foo@bar.org')
            self.assertEqual(session['email'], 'foo@bar.org')

            # Logout.
            rv = c.post('/logout', data=dict(_csrf_token='csrf!'))
            self.assertEqual(rv.status, '200 OK')
            self.assertEqual(rv.data, 'logged out')
            self.assertTrue('email' not in session)

    def test_csp_headers_exist(self):
        headers = ['X-Content-Security-Policy', 'Content-Security-Policy']
        prefix = "default-src 'self'"
        for path in ['/', '/aewg', '/lol/']:
            rv = self.app.get(path)
            for header in headers:
                self.assertTrue(rv.headers[header].startswith(prefix))

    def test_index_works(self):
        rv = self.app.get('/')
        self.assertEqual(rv.status, '200 OK')
        self.assertTrue('openbadges' in rv.data)

    def test_update_works(self):
        rv = self.app.post('/update')
        self.assertEqual(rv.status, '200 OK')
        self.assertEqual('update complete', rv.data)

    @mock.patch('fleeting.Project')
    @mock.patch('fleeting.Thread')
    def test_project_index_works(self, Thread, Project):
        Project.return_value.get_instances.return_value = [{
            'state': 'running',
            'slug': 'meh'
        }]
        rv = self.app.get('/openbadges/')
        Thread.assert_called_once_with(
            target=Project.return_value.get_instance_status,
            kwargs={'slug': 'meh'}
        )
        Thread.return_value.run.assert_called_once_with()
        self.assertEqual(rv.status, '200 OK')

    def test_invalid_project_index_raises_404(self):
        rv = self.app.get('/openbadgesuuuu/')
        self.assertEqual(rv.status, '404 NOT FOUND')
