import unittest

import fleeting

class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = fleeting.app.test_client()

    def test_csp_headers_exist(self):
        headers = ['X-Content-Security-Policy', 'Content-Security-Policy']
        prefix = "default-src 'self'"
        for path in ['/', '/aewg', '/openbadges/', '/lol/']:
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

    def test_project_index_works(self):
        rv = self.app.get('/openbadges/')
        self.assertEqual(rv.status, '200 OK')

    def test_invalid_project_index_raises_404(self):
        rv = self.app.get('/openbadgesuuuu/')
        self.assertEqual(rv.status, '404 NOT FOUND')
