import os
import time
import json
from threading import Thread
from functools import wraps

import browserid
import httplib2
from flask import Flask, Blueprint, abort, g, render_template, request, \
                  session, flash, redirect, escape
from .csrf import enable_csrf, csrf_exempt

from .project import Project, get_project_map

app = Flask(__name__)

enable_csrf(app)

def dot_min():
    if app.config['DEBUG']:
        return ''
    return '.min'

app.jinja_env.globals['email'] = lambda: session.get('email', '')
app.jinja_env.globals['dot_min'] = dot_min

def requires_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'email' not in session:
            abort(401)
        return f(*args, **kwargs)
    return wrapper

@app.after_request
def add_csp_headers(response):
    policy = "default-src 'self' https://login.persona.org " \
             "https://api.github.com"
    response.headers['Content-Security-Policy'] = policy
    response.headers['X-Content-Security-Policy'] = policy
    return response

project_bp = Blueprint('project', __name__, url_prefix='/<project>')

@project_bp.url_value_preprocessor
def pull_project(endpoint, values):
    pname = values.pop('project', None)
    if pname not in get_project_map():
        abort(404)
    g.project = Project(pname)

@project_bp.route('/create', methods=['POST'])
@requires_login
def create_instance():
    # TODO: Verify user/branch match a regexp, at least.
    user = request.form['user']
    branch = request.form['branch']
    slug = "%s.%s-%s" % (user, branch, str(int(time.time())))
    app.logger.info('attempting to create instance %s/%s on behalf of '
                    '%s.' % (g.project.id, slug, session['email']))
    result = g.project.create_instance(
        slug=slug,
        git_user=user,
        git_branch=branch,
        key_name=os.environ['AWS_KEY_NAME'],
        notify_topic=os.environ.get('AWS_NOTIFY_TOPIC'),
        security_groups=[os.environ['AWS_SECURITY_GROUP']]
    )
    if result == 'INVALID_GIT_INFO':
        flash('The git user and/or branch is invalid.', 'error')
    elif result == 'DONE':
        flash('The instance <strong>%s</strong> was created, and will '
              'appear shortly.' % escape(slug), 'success')
    else:
        flash('An unknown error occurred. Sorry!', 'error')
    return redirect('/%s/' % g.project.id)

@project_bp.route('/log')
@requires_login
def view_instance_log():
    slug = request.args.get('slug')
    log = g.project.get_instance_log(slug)
    if log is None:
        return "Unknown instance.", 404
    return (log, 200, {'Content-Type': 'text/plain'})

@project_bp.route('/destroy', methods=['POST'])
@requires_login
def destroy_instance():
    # TODO: Verify slug matches a regexp, at least.
    slug = request.form['slug']
    app.logger.info('attempting to destroy instance %s/%s on behalf of '
                    '%s.' % (g.project.id, slug, session['email']))
    g.project.destroy_instance(slug)
    flash('The instance <strong>%s</strong> has been scheduled for '
          'destruction, and will be removed shortly.' % escape(slug),
          'info')
    return redirect('/%s/' % g.project.id)

def render_project_template(name):
    instances = g.project.get_instances()
    for inst in instances:
        if inst['state'] == 'running' and 'url' not in inst:
            Thread(target=g.project.get_instance_status,
                   kwargs={'slug': inst['slug']}).run()
    return render_template(name,
                           project=g.project,
                           instances=instances)

@project_bp.route('/list')
def project_list():
    return render_project_template('project-list.html')

@project_bp.route('/')
def project_index():
    return render_project_template('project.html')

app.register_blueprint(project_bp)

@app.route('/login', methods=['POST'])
def login():
    origin = "%(PREFERRED_URL_SCHEME)s://%(SERVER_NAME)s" % (app.config)
    app.logger.info('processing assertion with origin %s' % origin)
    data = browserid.verify(request.form['assertion'], origin)
    session['email'] = data['email']
    return data['email']

@app.route('/logout', methods=['POST'])
def logout():
    if 'email' in session:
        del session['email']
    return 'logged out'

def delayed(func, seconds):
    @wraps(func)
    def wrapper(*args, **kwargs):
        app.logger.info('waiting %d seconds to execute %s' % (seconds,
                                                              func.__name__))
        time.sleep(seconds)
        wrapper.wrapped(*args, **kwargs)
    wrapper.wrapped = func
    return wrapper

@csrf_exempt
@app.route('/update', methods=['POST'])
def update():
    info = json.loads(request.data)
    if 'SubscribeURL' in info:
        http = httplib2.Http(timeout=3,
                             disable_ssl_certificate_validation=True)
        res, content = http.request(info['SubscribeURL'])
        app.logger.info('subscribed at %s.' % info['SubscribeURL'])
        return 'subscribed'
    msg = json.loads(info['Message'])
    if ('AutoScalingGroupName' in msg and
        msg.get('Event') == 'autoscaling:EC2_INSTANCE_TERMINATE'):
        groupname = msg['AutoScalingGroupName']
        for name in get_project_map():
            project = Project(name)
            if groupname.startswith(project.autoscale_group_name_prefix):
                app.logger.info('scheduling cleanup for %s' % name)
                Thread(target=delayed(project.cleanup_instances, 15),
                       kwargs=dict(logger=app.logger)).run()
    return 'updated'

@app.route('/')
def index():
    projects = [Project(name) for name in get_project_map()]
    return render_template('index.html', projects=projects)
