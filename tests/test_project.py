import unittest
import json
from StringIO import StringIO

import mock

from fleeting import project

class ProjectTests(unittest.TestCase):
    def test_get_project_map_works(self):
        pmap = project.get_project_map()
        self.assertTrue('openbadges' in pmap)

    def test_project_reads_meta_info(self):
        proj = project.Project('openbadges')
        self.assertEqual(proj.meta['name'], 'Open Badges Backpack')
        self.assertEqual(proj.meta['repo'], 'mozilla/openbadges')

    @mock.patch('boto.connect_ec2')
    def test_project_get_instances_works(self, connect_ec2):
        instance = mock.MagicMock(
            tags={'fleeting:openbadges': json.dumps(dict(
                      git_user='lol',
                      git_branch='cat'
                  )),
                  'fleeting:openbadges:ready': 'http://foo/'},
            state='hi state',
            launch_time='2013-04-29T11:53:42.000Z'
        )
        res = mock.MagicMock(instances=[instance])
        connect_ec2.return_value.get_all_instances.return_value = [res]
        proj = project.Project('openbadges')
        self.assertEqual(proj.get_instances(), [{
            'url': 'http://foo/',
            'state': 'hi state',
            'git_user': 'lol',
            'git_branch': 'cat',
            'git_branch_url': 'https://github.com/lol/openbadges/tree/cat',
            'launch_time': '2013-04-29T11:53:42.000Z'
        }])

    @mock.patch('fleeting.project.Project')
    def test_cmdline(self, Project):
        Project.return_value.get_instances.return_value = ['hi']
        output = StringIO()
        project.cmdline(['list'], output)
        self.assertEqual(output.getvalue(), "'hi'\n")
