import os
import rfc822
import json
import unittest

import browserid
from flask import session
import mock

import fleeting
import fleeting.csrf
from .test_project import create_mock_http_response

ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *x: os.path.join(ROOT, *x)

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

@fleeting.app.route('/csrf')
def generate_csrf():
    return fleeting.app.jinja_env.globals['csrf_token']()

def postdata(**kwargs):
    kwargs.update({'_csrf_token': 'csrf!'})
    return kwargs

def load_message(filename):
    msg = open(filename, 'r')
    headers = rfc822.Message(msg)
    body = msg.read()
    header_dict = {}
    for name in headers:
        header_dict[name] = headers.get(name)
    return header_dict, body

class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = fleeting.app.test_client()
 
    def login(self, email):
        self.app.get('/csrf')
        self.app.post('/login', data=postdata(assertion=email))

    def test_csrf_works(self):
        rv = self.app.post('/logout')
        self.assertEqual(rv.status, '400 BAD REQUEST')

    def test_login_and_logout_work(self):
        with fleeting.app.test_client() as c:
            # Set the CSRF token.
            c.get('/csrf')
            self.assertTrue('email' not in session)

            # Login.
            rv = c.post('/login', data=postdata(assertion='foo@bar.org'))
            self.assertEqual(rv.status, '200 OK')
            self.assertEqual(rv.data, 'foo@bar.org')
            self.assertEqual(session['email'], 'foo@bar.org')

            # Logout.
            rv = c.post('/logout', data=postdata())
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

    def test_project_destroy_instance_requires_login(self):
        self.app.get('/csrf') # Set CSRF token.
        rv = self.app.post('/openbadges/destroy', data=postdata())
        self.assertEqual(rv.status, '401 UNAUTHORIZED')

    def test_update_works_with_termination_notification(self):
        Project = fleeting.Project
        openbadges = Project('openbadges')
        openbadges.cleanup_instances = mock.MagicMock()
        openbadges.cleanup_instances.return_value = (2, 0)

        def FakeProject(name):
            if name == 'openbadges':
                return openbadges
            proj = Project(name)
            proj.cleanup_instances = lambda: IShouldNotBeCalled()
            return proj

        with mock.patch('fleeting.Project', FakeProject):
            headers, body = load_message(path('termination.txt'))
            rv = self.app.post('/update', headers=headers, data=body)
            self.assertEqual(rv.status, '200 OK')
            self.assertEqual('updated', rv.data)
            openbadges.cleanup_instances.assert_called_once_with()

    @mock.patch('httplib2.Http')
    def test_update_works_with_subscription_confirmation(self, http):
        headers, body = load_message(path('subscription-confirmation.txt'))
        create_mock_http_response(http, status=200)
        rv = self.app.post('/update', headers=headers, data=body)
        self.assertEqual(rv.status, '200 OK')
        self.assertEqual('subscribed', rv.data)
        http.assert_called_once_with(disable_ssl_certificate_validation=True,
                                     timeout=3)
        http.return_value.request.assert_called_once_with(
            json.loads(body)['SubscribeURL']
        )

    @mock.patch('fleeting.Project')
    @mock.patch('fleeting.flash')
    def test_project_destroy_instance_works(self, flash, Project):
        Project.return_value.id = 'openbadges'
        self.login('meh@goo.org')
        rv = self.app.post('/openbadges/destroy', data=postdata(slug='bu'))
        self.assertEqual(rv.status, '302 FOUND')
        self.assertEqual(rv.headers['location'], 'http://foo.org/openbadges/')
        Project.return_value.destroy_instance.assert_called_once_with('bu')
        self.assertTrue('<strong>bu</strong>' in flash.call_args[0][0])

    @mock.patch('fleeting.Project')
    @mock.patch('fleeting.flash')
    @mock.patch('time.time', lambda: 12.3)
    @mock.patch('os.environ', dict(
        AWS_KEY_NAME='keyname',
        AWS_SECURITY_GROUP='secgroup'
    ))
    def flash_from_project_create_instance(self, rv, flash, Project):
        Project.return_value.id = 'openbadges'
        Project.return_value.create_instance.return_value = rv
        self.login('meh@goo.org')
        rv = self.app.post('/openbadges/create', data=postdata(
            user='uzer',
            branch='branchu'
        ))
        Project.return_value.create_instance.assert_called_once_with(
            key_name='keyname',
            git_branch=u'branchu',
            git_user=u'uzer',
            notify_topic=None,
            slug=u'uzer.branchu-12',
            security_groups=['secgroup']
        )
        self.assertEqual(rv.status, '302 FOUND')
        self.assertEqual(rv.headers['location'], 'http://foo.org/openbadges/')
        return flash.call_args

    def test_project_create_instance_reports_success(self):
        args, _ = self.flash_from_project_create_instance('DONE')
        self.assertTrue('<strong>uzer.branchu-12</strong>' in args[0])
        self.assertEqual(args[1], 'success')

    def test_project_create_instance_reports_invalid_git_info(self):
        args, _ = self.flash_from_project_create_instance('INVALID_GIT_INFO')
        self.assertTrue('git' in args[0])
        self.assertEqual(args[1], 'error')

    def test_project_create_instance_reports_unknown_error(self):
        args, _ = self.flash_from_project_create_instance('BLARGLE')
        self.assertTrue('unknown' in args[0])
        self.assertEqual(args[1], 'error')

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
