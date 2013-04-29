import unittest
import json
from StringIO import StringIO

import mock

from fleeting import project

def create_mock_instance(ec2):
    instance = mock.MagicMock(
        tags={'fleeting:openbadges': json.dumps(dict(
                  git_user='toolness',
                  git_branch='experimentz',
                  slug='sluggy'
              )),
              'fleeting:openbadges:ready': 'http://foo/'},
        state='running',
        launch_time='2013-04-29T11:53:42.000Z'
    )
    res = mock.MagicMock(instances=[instance])
    ec2.return_value.get_all_instances.return_value = [res]
    return instance

class ProjectTests(unittest.TestCase):
    def setUp(self):
        project._ec2_conn = None
        project._ec2_autoscale_conn = None

    def test_get_project_map_works(self):
        pmap = project.get_project_map()
        self.assertTrue('openbadges' in pmap)

    def test_project_reads_meta_info(self):
        proj = project.Project('openbadges')
        self.assertEqual(proj.meta['name'], 'Open Badges Backpack')
        self.assertEqual(proj.meta['repo'], 'mozilla/openbadges')

    def test_get_instance_ready_url_works(self):
        proj = project.Project('openbadges')
        url = proj._get_instance_ready_url('boop.org')
        self.assertEqual(url, 'http://boop.org:8888/')

    @mock.patch('boto.connect_ec2')
    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_project_cleanup_instances_works(self, asc, ec2):
        proj = project.Project('openbadges')

        create_mock_instance(ec2)

        ag = [mock.MagicMock(min_size=0, instances=[])]
        asc.return_value.get_all_groups.return_value = ag
        lc = [mock.MagicMock()]
        lc[0].delete.side_effect = Exception()
        asc.return_value.get_all_launch_configurations.return_value = lc

        deleted, errors = proj.cleanup_instances()
        self.assertEqual(deleted, 1)
        self.assertEqual(errors, 1)

        ec2.assert_called_once_with()
        ec2.return_value.get_all_instances.assert_called_once_with(
            filters={'instance-state-name': ['terminated'],
                     'tag-key': 'fleeting:openbadges'}
        )
        asc.return_value.get_all_groups.assert_called_once_with(
            names=[u'fleeting_autoscale_openbadges_sluggy']
        )
        asc.return_value.get_all_launch_configurations.assert_called_once_with(
            names=[u'fleeting_launchconfig_openbadges_sluggy']
        )
        ag[0].delete.assert_called_once_with()
        lc[0].delete.assert_called_once_with()

    @mock.patch('boto.connect_ec2')
    def test_project_get_instances_works(self, connect_ec2):
        create_mock_instance(connect_ec2)
        proj = project.Project('openbadges')
        self.assertEqual(proj.get_instances(), [{
            'url': 'http://foo/',
            'state': 'running',
            'git_user': 'toolness',
            'git_branch': 'experimentz',
            'slug': 'sluggy',
            'git_branch_url': 'https://github.com/toolness/openbadges/tree/experimentz',
            'launch_time': '2013-04-29T11:53:42.000Z'
        }])
