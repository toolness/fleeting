import os
import re
import json
import datetime
import logging

import boto
from boto.ec2.autoscale import LaunchConfiguration
from boto.ec2.autoscale import AutoScalingGroup
from boto.ec2.autoscale import AutoScaleConnection
import httplib2
from jinja2 import Template

from .utils import path
from .tempcache import DictTempCache

AUTHSERVER_PORT = 9312
AUTHSERVER_CREDS = "fleeting:fleeting"
AUTHSERVER_LOGFILE = "log.txt"
BOOTSTRAP_TEMPLATE = open(path('templates', 'bootstrap.sh')).read()

DEFAULT_LIFETIME = datetime.timedelta(hours=24)
DEFAULT_CACHE_TTL = 3600

cache = DictTempCache(DEFAULT_CACHE_TTL)
_ec2_conn = None
_ec2_autoscale_conn = None

def connect_ec2():
    global _ec2_conn
    if not _ec2_conn:
        _ec2_conn = boto.connect_ec2()
    return _ec2_conn

def connect_ec2_autoscale():
    global _ec2_autoscale_conn
    if not _ec2_autoscale_conn:
        _ec2_autoscale_conn = AutoScaleConnection()
    return _ec2_autoscale_conn

def does_url_404(url):
    http = httplib2.Http(timeout=3,
                         disable_ssl_certificate_validation=True)
    res, content = http.request(url, method='HEAD')
    if res.status == 404:
        return True
    return False

class Project(object):
    def __init__(self, project_id):
        pmap = get_project_map()
        self.id = project_id
        self.script_path = pmap[project_id]
        self.script_template = open(self.script_path, 'r').read()
        self.meta = {}
        self.tag_name = 'fleeting:%s' % project_id
        self.ready_tag_name = '%s:ready' % self.tag_name
        self.autoscale_group_name_prefix = 'fleeting_autoscale_%s' % self.id
        for line in self.script_template.splitlines():
            match = re.search(r'fleeting-meta:([a-z0-9\-]+)\s*=(.*)', line)
            if match:
                self.meta[match.group(1)] = match.group(2).strip()

    def _set_cache_entry(self, slug, value):
        cache['%s:%s' % (self.tag_name, slug)] = value

    def _get_launch_config_name(self, slug):
        return 'fleeting_launchconfig_%s_%s' % (self.id, slug)

    def _get_autoscale_group_name(self, slug):
        return '%s_%s' % (self.autoscale_group_name_prefix, slug)

    def _get_instance_ready_url(self, hostname):
        return self.meta['ready-url'].replace('localhost', hostname)

    def _get_github_url(self, github_user, github_branch):
        return 'https://github.com/%s/%s/tree/%s' % (
            github_user,
            self.meta['repo'].split('/')[1],
            github_branch
        )

    def cleanup_instances(self, logger=logging):
        logger.info('cleaning up project %s' % self.id)
        s = {'deleted': 0, 'errors': 0}
        ec2 = connect_ec2()
        conn = connect_ec2_autoscale()
        reservations = ec2.get_all_instances(filters={
            'tag-key': self.tag_name,
            'instance-state-name': ['terminated']
        })

        def try_deleting(obj):
            try:
                obj.delete()
                s['deleted'] += 1
            except Exception, e:
                s['errors'] += 1

        for res in reservations:
            slug = json.loads(res.instances[0].tags[self.tag_name])['slug']
            ag_name = self._get_autoscale_group_name(slug)
            ag = conn.get_all_groups(names=[ag_name])
            if ag and ag[0].min_size == 0 and not ag[0].instances:
                try_deleting(ag[0])
            lc_name = self._get_launch_config_name(slug)
            lc = conn.get_all_launch_configurations(names=[lc_name])
            if lc:
                try_deleting(lc[0])
        logger.info('%d deleted, %d errors in %s' % (
            s['deleted'], s['errors'], self.id
        ))
        return (s['deleted'], s['errors'])

    def get_instances(self):
        ec2 = connect_ec2()
        reservations = ec2.get_all_instances(filters={
            'tag-key': self.tag_name,
            'instance-state-name': ['pending', 'running']
        })
        instances = {}
        for res in reservations:
            inst = res.instances[0]
            info = json.loads(inst.tags[self.tag_name])
            info['launch_time'] = inst.launch_time
            info['state'] = inst.state
            if self.ready_tag_name in inst.tags:
                info['url'] = inst.tags[self.ready_tag_name]
            instances[info['slug']] = info
        for item in cache.find('%s:' % self.tag_name):
            if (item['state'] == 'pending' and
                item['slug'] not in instances):
                instances[item['slug']] = item
            elif (item['state'] == 'terminated' and
                  item['slug'] in instances):
                del instances[item['slug']]
        for info in instances.values():
            info['git_branch_url'] = self._get_github_url(info['git_user'],
                                                          info['git_branch'])
        return instances.values()

    def _ping_ready_url(self, inst):
        state = 'INSTANCE:%s' % inst.state
        info = None

        if inst.state == 'running' and inst.public_dns_name:
            url = self._get_instance_ready_url(inst.public_dns_name)
            http = httplib2.Http(timeout=3)
            try:
                res, content = http.request(url)
                if res.status == 200:
                    state = 'READY'
                    info = url
                    inst.add_tag(self.ready_tag_name, url)
                else:
                    raise Exception('status %d' % res.status)
            except Exception, e:
                info = str(e)
        return (state, info)

    def _get_running_instance(self, slug):
        ec2 = connect_ec2()
        reservations = ec2.get_all_instances(filters={
            'tag-key': self.tag_name,
            'instance-state-name': ['running']
        })
        instances = {}
        for res in reservations:
            inst = res.instances[0]
            info = json.loads(inst.tags[self.tag_name])
            if info['slug'] == slug:
                return inst

    def get_instance_authserver_log(self, slug):
        inst = self._get_running_instance(slug)
        if not inst:
            return None
        if inst.public_dns_name:
            user, passwd = AUTHSERVER_CREDS.split(':')
            url = "http://%s:%d/%s" % (inst.public_dns_name,
                                       AUTHSERVER_PORT,
                                       AUTHSERVER_LOGFILE)
            http = httplib2.Http(timeout=5)
            http.add_credentials(user, passwd)
            try:
                res, content = http.request(url)
                if res.status == 200:
                    return content
            except Exception, e:
                pass
            return ""

    def get_instance_log(self, slug):
        inst = self._get_running_instance(slug)
        if not inst:
            return None
        return inst.get_console_output().output or ""

    def get_instance_status(self, slug):
        conn = connect_ec2_autoscale()
        ag_name = self._get_autoscale_group_name(slug)
        ag = conn.get_all_groups(names=[ag_name])
        if not ag:
            return ('NOT_FOUND', None)
        if not ag[0].instances:
            if ag[0].min_size == 1:
                return ('INSTANCE_DOES_NOT_YET_EXIST', None)
            return ('INSTANCE_DOES_NOT_EXIST', None)
        ec2 = connect_ec2()
        res = ec2.get_all_instances([ag[0].instances[0].instance_id])
        inst = res[0].instances[0]


        if self.ready_tag_name in inst.tags:
            return ('READY', inst.tags[self.ready_tag_name])

        return self._ping_ready_url(inst)

    def destroy_instance(self, slug):
        self._set_cache_entry(slug, dict(
            slug=slug,
            state='terminated'
        ))
        found = False

        conn = connect_ec2_autoscale()
        ag_name = self._get_autoscale_group_name(slug)
        ag = conn.get_all_groups(names=[ag_name])
        if ag:
            try:
                ag[0].delete()
                found = True
            except boto.exception.BotoServerError, e:
                if e.code == 'ResourceInUse':
                    ag[0].shutdown_instances()
                    return 'SHUTDOWN_IN_PROGRESS'
                return 'ERROR:%s' % e.code

        lc_name = self._get_launch_config_name(slug)
        lc = conn.get_all_launch_configurations(names=[lc_name])
        if lc:
            try:
                lc[0].delete()
                found = True
            except boto.exception.BotoServerError, e:
                return 'ERROR:%s' % e.code

        if found:
            return 'DONE'
        return 'NOT_FOUND'

    def render_user_data(self, **kwargs):
        kwargs.update(dict(globals()))
        sp = Template(self.script_template).render(**kwargs)
        kwargs['STARTPROJECT_SCRIPT'] = sp
        return Template(BOOTSTRAP_TEMPLATE).render(**kwargs)

    def create_instance(self, slug, git_user, git_branch, key_name,
                        security_groups, notify_topic=None,
                        lifetime=DEFAULT_LIFETIME):
        if does_url_404(self._get_github_url(git_user, git_branch)):
            return 'INVALID_GIT_INFO'

        conn = connect_ec2_autoscale()
        ag_name = self._get_autoscale_group_name(slug)

        ag = conn.get_all_groups(names=[ag_name])
        if ag and (ag[0].instances or ag[0].min_size == 1):
            return 'INSTANCE_ALREADY_EXISTS'

        self.cleanup_instances()

        lc = LaunchConfiguration(
            name=self._get_launch_config_name(slug),
            image_id=self.meta['image-id'],
            key_name=key_name,
            instance_type=self.meta['instance-type'],
            security_groups=security_groups,
            user_data=self.render_user_data(
                GIT_USER=git_user,
                GIT_BRANCH=git_branch
            )
        )
        conn.create_launch_configuration(lc)

        info = dict(
            slug=slug,
            git_user=git_user,
            git_branch=git_branch,
            lifetime=lifetime.total_seconds()
        )
        ag_shutdown_name = '%s_shutdown-action' % ag_name
        ag_tag = boto.ec2.autoscale.tag.Tag(
            conn,
            self.tag_name,
            json.dumps(info),
            propagate_at_launch=True,
            resource_id=ag_name
        )
        ag = AutoScalingGroup(
            group_name=ag_name,
            availability_zones=[
                'us-east-1a',
                'us-east-1b',
                'us-east-1c',
                'us-east-1d',
            ],
            tags=[ag_tag],
            launch_config=lc,
            min_size=1,
            max_size=1,
            connection=conn
        )
        conn.create_auto_scaling_group(ag)
        conn.create_scheduled_group_action(
            ag_name,
            ag_shutdown_name,
            datetime.datetime.utcnow() + lifetime,
            desired_capacity=0,
            min_size=0,
            max_size=0
        )
        if notify_topic:
            conn.put_notification_configuration(
                ag,
                notify_topic,
                ['autoscaling:EC2_INSTANCE_TERMINATE']
            )
        info['state'] = 'pending'
        self._set_cache_entry(slug, info)
        return 'DONE'

def get_project_map():
    pmap = {}
    projects_dir = path('projects')
    for filename in os.listdir(projects_dir):
        if not filename.startswith('.'):
            abspath = os.path.join(projects_dir, filename)
            pmap[os.path.splitext(filename)[0]] = abspath
    return pmap
