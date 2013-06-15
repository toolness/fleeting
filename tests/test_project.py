import unittest
import json
from StringIO import StringIO

import mock
from boto.exception import BotoServerError

from fleeting import project
from fleeting.tempcache import DictTempCache

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

def create_mock_launch_config(asc):
    lc = mock.MagicMock()
    asc.return_value.get_all_launch_configurations.return_value = [lc]
    return lc

def create_mock_http_response(http, status, content=''):
    res = mock.MagicMock(status=status)
    http.return_value.request.return_value = (res, content)
    return res

def create_server_error(code):
    err = BotoServerError('', '', '')
    err.error_code = code
    return err

class ProjectTests(unittest.TestCase):
    def setUp(self):
        project._ec2_conn = None
        project._ec2_autoscale_conn = None
        project.cache = DictTempCache(project.DEFAULT_CACHE_TTL)

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

    @mock.patch('httplib2.Http')
    def test_does_url_404_returns_true(self, http):
        create_mock_http_response(http, status=404)
        self.assertEqual(project.does_url_404('http://foo.org/'), True)

    @mock.patch('httplib2.Http')
    def test_does_url_404_returns_false(self, http):
        create_mock_http_response(http, status=200)
        self.assertEqual(project.does_url_404('http://foo.org/'), False)

    @mock.patch('fleeting.project.does_url_404')
    def test_create_instance_returns_on_bad_github_info(self, does_url_404):
        does_url_404.return_value = True
        proj = project.Project('openbadges')
        r = proj.create_instance('z', 'uzer', 'branchu', 'key', ['default'])
        self.assertEqual(r, 'INVALID_GIT_INFO')
        does_url_404.assert_called_once_with(
            'https://github.com/uzer/openbadges/tree/branchu'
        )

    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_destroy_instance_shuts_down_instances(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instance_id='k', min_size=1)
        ag.delete.side_effect = create_server_error('ResourceInUse')
        self.assertEqual(proj.destroy_instance('ded'), 'SHUTDOWN_IN_PROGRESS')

    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_destroy_instance_catches_misc_autoscale_errors(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instance_id='k', min_size=1)
        ag.delete.side_effect = create_server_error('Oopsie')
        self.assertEqual(proj.destroy_instance('ded'), 'ERROR:Oopsie')

    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_destroy_instance_catches_misc_launch_config_errors(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instance_id='k', min_size=1)
        lc = create_mock_launch_config(asc)
        lc.delete.side_effect = create_server_error('Ack')
        self.assertEqual(proj.destroy_instance('ded'), 'ERROR:Ack')

    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_destroy_instance_returns_not_found(self, asc):
        proj = project.Project('openbadges')
        ascrv = asc.return_value

        ascrv.get_all_groups.return_value = []
        ascrv.get_all_launch_configurations.return_value = []

        self.assertEqual(proj.destroy_instance('ded'), 'NOT_FOUND')

    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_destroy_instance_adds_cache_entry(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instance_id='k', min_size=1)
        lc = create_mock_launch_config(asc)
        proj.destroy_instance('buk')
        self.assertEqual(project.cache.find('fleeting:openbadges:buk'), [{
            'slug': 'buk',
            'state': 'terminated'
        }])

    @mock.patch('fleeting.project.AutoScaleConnection')
    def test_destroy_instance_returns_done(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instance_id='k', min_size=1)
        lc = create_mock_launch_config(asc)

        self.assertEqual(proj.destroy_instance('buk'), 'DONE')

        ag.delete.assert_called_once_with()
        lc.delete.assert_called_once_with()

        ascrv = asc.return_value

        ascrv.get_all_groups.assert_called_once_with(
            names=['fleeting_autoscale_openbadges_buk']
        )
        ascrv.get_all_launch_configurations.assert_called_once_with(
            names=['fleeting_launchconfig_openbadges_buk']
        )

    @mock.patch('fleeting.project.AutoScaleConnection')
    @mock.patch('fleeting.project.does_url_404', lambda x: False)
    def test_create_instance_returns_when_instance_exists(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instance_id='q', min_size=1)
        r = proj.create_instance('z', 'uzer', 'branchu', 'key', ['default'])
        self.assertEqual(r, 'INSTANCE_ALREADY_EXISTS')
        asc.return_value.get_all_groups.assert_called_once_with(
            names=['fleeting_autoscale_openbadges_z']
        )

    @mock.patch('fleeting.project.AutoScaleConnection')
    @mock.patch('fleeting.project.does_url_404', lambda x: False)
    def test_create_instance_adds_cache_entry(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instances=[], min_size=0)
        with mock.patch.object(proj, 'cleanup_instances') as ci:
            proj.create_instance('z', 'uzer', 'branchu', 'key',
                                 security_groups=['default'])
            self.assertEqual(
                project.cache.find('fleeting:openbadges:z'),
                [dict(slug='z',
                      state='pending',
                      lifetime=86400.0,
                      git_user='uzer',
                      git_branch='branchu')]
            )

    @mock.patch('fleeting.project.AutoScaleConnection')
    @mock.patch('fleeting.project.does_url_404', lambda x: False)
    def test_create_instance_works(self, asc):
        proj = project.Project('openbadges')
        ag = create_mock_autoscale_group(asc, instances=[], min_size=0)
        with mock.patch.object(proj, 'cleanup_instances') as ci:
            r = proj.create_instance('z', 'uzer', 'branchu', 'key',
                                     security_groups=['defaultr'],
                                     notify_topic='notifytopik')
            self.assertEqual(r, 'DONE')
            ci.assert_called_once_with()
            ascrv = asc.return_value

            lc = ascrv.create_launch_configuration.call_args[0][0]
            self.assertEqual(lc.name, 'fleeting_launchconfig_openbadges_z')
            self.assertEqual(lc.key_name, 'key')
            self.assertEqual(lc.security_groups, ['defaultr'])
            self.assertTrue('uzer' in lc.user_data)
            self.assertTrue('branchu' in lc.user_data)

            # TODO: Ensure autoscale group tag is ok

            ag = ascrv.create_auto_scaling_group.call_args[0][0]
            self.assertEqual(ag.name, 'fleeting_autoscale_openbadges_z')

            # TODO: Ensure conn.create_scheduled_group_action() is ok
            # TODO: Ensure conn.put_notification_configuration() is ok

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
    def test_get_instance_returns_instance(self, ec2):
        proj = project.Project('openbadges')
        inst = create_mock_instance(ec2)
        self.assertEqual(proj.get_instance('sluggy'), inst)

    @mock.patch('httplib2.Http')
    def test_get_instance_authserver_log_returns_nonempty_str(self, http):
        proj = project.Project('openbadges')
        create_mock_http_response(http, status=200, content='blah')
        inst = mock.MagicMock(state='running', public_dns_name='foo.org')
        self.assertEqual(proj.get_instance_authserver_log(inst), 'blah')

        h = http.return_value
        h.add_credentials.assert_called_once_with('fleeting', 'fleeting')
        h.request.assert_called_once_with('http://foo.org:9312/log.txt')

    @mock.patch('httplib2.Http')
    def test_get_instance_authserver_log_returns_empty_str(self, http):
        proj = project.Project('openbadges')
        http.return_value.request.side_effect = Exception('funky socket err')
        inst = mock.MagicMock(state='running', public_dns_name='foo.org')
        self.assertEqual(proj.get_instance_authserver_log(inst), '')

    def test_get_instance_log_returns_nonempty_str(self):
        proj = project.Project('openbadges')
        inst = mock.MagicMock()
        inst.get_console_output.return_value.output = "LOL"
        self.assertEqual(proj.get_instance_log(inst), "LOL")

    def test_get_instance_log_returns_empty_str(self):
        proj = project.Project('openbadges')
        inst = mock.MagicMock()
        inst.get_console_output.return_value.output = None
        self.assertEqual(proj.get_instance_log(inst), "")

    @mock.patch('boto.connect_ec2')
    def test_get_instance_returns_none(self, ec2):
        proj = project.Project('openbadges')
        inst = create_mock_instance(ec2)
        self.assertEqual(proj.get_instance('blop'), None)

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
        create_mock_http_response(http, status=500)
        self.assertEqual(project.Project('openbadges')._ping_ready_url(inst),
                         ('INSTANCE:running', 'status 500'))

    @mock.patch('httplib2.Http')
    def test_ping_ready_url_handles_good_http_status(self, http):
        inst = mock.MagicMock(state='running', public_dns_name='u.org')
        create_mock_http_response(http, status=200)
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
        lc = create_mock_launch_config(asc)
        lc.delete.side_effect = Exception()

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
        lc.delete.assert_called_once_with()

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

    @mock.patch('boto.connect_ec2')
    def test_project_get_instances_adds_cache_entries(self, connect_ec2):
        proj = project.Project('openbadges')
        project.cache['fleeting:openbadges:foo'] = dict(
            slug='foo',
            state='pending',
            lifetime=86400.0,
            git_user='uzer',
            git_branch='branchu'
        )
        self.assertEqual(proj.get_instances(), [{
            'state': 'pending',
            'git_user': 'uzer',
            'git_branch': 'branchu',
            'lifetime': 86400.0,
            'slug': 'foo',
            'git_branch_url': 'https://github.com/uzer/openbadges/tree/branchu'
        }])

    @mock.patch('boto.connect_ec2')
    def test_project_get_instances_removes_cache_entries(self, connect_ec2):
        create_mock_instance(connect_ec2)
        proj = project.Project('openbadges')
        project.cache['fleeting:openbadges:sluggy'] = dict(
            slug='sluggy',
            state='terminated'
        )
        self.assertEqual(proj.get_instances(), [])
