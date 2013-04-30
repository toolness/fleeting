import unittest
import json
from StringIO import StringIO

import mock

from fleeting import project

def create_mock_instance(ec2, ready_tag=True):
    tags = {
        'fleeting:openbadges': json.dumps(dict(
            git_user='toolness',
            git_branch='experimentz',
            slug='sluggy'
        ))
    }
    if ready_tag:
        tags['fleeting:openbadges:ready'] = 'http://foo/'
    instance = mock.MagicMock(
        tags=tags,
        state='running',
        launch_time='2013-04-29T11:53:42.000Z'
    )
    res = mock.MagicMock(instances=[instance])
    ec2.return_value.get_all_instances.return_value = [res]
    return instance

def create_mock_autoscale_group(asc, instance_id=None, **kwargs):
    if not kwargs:
        ag = []
    else:
        if instance_id:
            kwargs['instances'] = [mock.MagicMock(instance_id=instance_id)]
        ag = [mock.MagicMock(**kwargs)]
    asc.return_value.get_all_groups.return_value = ag
    if ag:
        return ag[0]

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

    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_get_instance_status_returns_not_found(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc)
        self.assertEqual(proj.get_instance_status('zzz'),
                         ('NOT_FOUND', None))
        asc.return_value.get_all_groups.assert_called_once_with(
            names=['fleeting_autoscale_openbadges_zzz']
        )

    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_get_instance_status_returns_instance_not_yet_exists(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instances=[], min_size=1)
        self.assertEqual(proj.get_instance_status('zzz'),
                         ('INSTANCE_DOES_NOT_YET_EXIST', None))

    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_get_instance_status_returns_instance_does_not_exist(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instances=[], min_size=0)
        self.assertEqual(proj.get_instance_status('zzz'),
                         ('INSTANCE_DOES_NOT_EXIST', None))

    @mock.patch('boto.connect_ec2')
    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_get_instance_status_returns_ready_tag(self, asc, ec2):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instance_id='z', min_size=0)
        inst = create_mock_instance(ec2)
        self.assertEqual(proj.get_instance_status('zzz'),
                         ('READY', 'http://foo/'))
        ec2.return_value.get_all_instances.assert_called_once_with(['z'])

    @mock.patch('boto.connect_ec2')
    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_get_instance_status_pings_ready_url(self, asc, ec2):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instance_id='z', min_size=0)
        inst = create_mock_instance(ec2, ready_tag=False)

        with mock.patch.object(proj, '_ping_ready_url') as ping:
            ping.return_value = ('HOORAY', 'cool')
            self.assertEqual(proj.get_instance_status('zzz'),
                             ('HOORAY', 'cool'))
            ping.assert_called_once_with(inst)

    def test_ping_ready_url_handles_no_public_dns_name(self):
        inst = mock.MagicMock(state='running', public_dns_name=None)
        self.assertEqual(project.Project('openbadges')._ping_ready_url(inst),
                         ('INSTANCE:running', None))

    @mock.patch('httplib2.Http')
    def test_ping_ready_url_handles_http_exceptions(self, http):
        inst = mock.MagicMock(state='running', public_dns_name='u.org')
        http.return_value.request.side_effect = Exception('funky socket err')
        self.assertEqual(project.Project('openbadges')._ping_ready_url(inst),
                         ('INSTANCE:running', 'funky socket err'))

    @mock.patch('httplib2.Http')
    def test_ping_ready_url_handles_bad_http_status(self, http):
        inst = mock.MagicMock(state='running', public_dns_name='u.org')
        http.return_value.request.return_value = (mock.MagicMock(status=500),
                                                  '')
        self.assertEqual(project.Project('openbadges')._ping_ready_url(inst),
                         ('INSTANCE:running', 'status 500'))

    @mock.patch('httplib2.Http')
    def test_ping_ready_url_handles_good_http_status(self, http):
        inst = mock.MagicMock(state='running', public_dns_name='u.org')
        http.return_value.request.return_value = (mock.MagicMock(status=200),
                                                  '')
        self.assertEqual(project.Project('openbadges')._ping_ready_url(inst),
                         ('READY', 'http://u.org:8888/'))
        inst.add_tag.assert_called_once_with('fleeting:openbadges:ready',
                                             'http://u.org:8888/')

    @mock.patch('boto.connect_ec2')
    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_project_cleanup_instances_works(self, asc, ec2):
        proj = project.Project('openbadges')

        create_mock_instance(ec2)
        ag = create_mock_autoscale_group(asc, min_size=0, instances=[])
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
        ag.delete.assert_called_once_with()
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
