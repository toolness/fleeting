import unittest

from fleeting import project

class ProjectTests(unittest.TestCase):
    def test_get_project_map_works(self):
        pmap = project.get_project_map()
        self.assertTrue('openbadges' in pmap)

    def test_project_reads_meta_info(self):
        proj = project.Project('openbadges')
        self.assertEqual(proj.meta['name'], 'Open Badges Backpack')
        self.assertEqual(proj.meta['repo'], 'mozilla/openbadges')
