import unittest

import fleeting

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.app = fleeting.app.test_client()

    def test_get_project_map_works(self):
        pmap = fleeting.get_project_map()
        self.assertTrue('openbadges' in pmap)

    def test_project_index_works(self):
        rv = self.app.get('/openbadges/')
        self.assertEqual(rv.status, '200 OK')

    def test_invalid_project_index_raises_404(self):
        rv = self.app.get('/openbadgesuuuu/')
        self.assertEqual(rv.status, '404 NOT FOUND')

    def test_project_reads_meta_info(self):
        proj = fleeting.Project('openbadges',
                                fleeting.path('projects/openbadges.sh'))
        self.assertEqual(proj.meta['name'], 'Open Badges Backpack')
        self.assertEqual(proj.meta['repo'], 'mozilla/openbadges')

class Tests(unittest.TestCase):
    def setUp(self):
        self.app = fleeting.app.test_client()

    def test_index_works(self):
        rv = self.app.get('/')
        self.assertEqual(rv.status, '200 OK')
        self.assertTrue('openbadges' in rv.data)

    def test_update_works(self):
        rv = self.app.post('/update')
        self.assertEqual(rv.status, '200 OK')
        self.assertEqual('update complete', rv.data)

if __name__ == '__main__':
    unittest.main()
