import os
import time
from threading import Thread
from functools import wraps

import browserid
from flask import Flask, Blueprint, abort, g, render_template, request, \
                  session, flash, redirect, escape
from .csrf import enable_csrf, csrf_exempt

from .project import Project, get_project_map

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

enable_csrf(app)

app.jinja_env.globals['email'] = lambda: session.get('email', '')

def requires_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'email' not in session:
            abort(401)
        return f(*args, **kwargs)
    return wrapper

@app.after_request
def add_csp_headers(response):
    policy = "default-src 'self' https://login.persona.org"
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
              'appear shortly.' % escape(slug))
    else:
        flash('An unknown error occurred. Sorry!', 'error')
    return redirect('/%s/' % g.project.id)

@project_bp.route('/destroy', methods=['POST'])
@requires_login
def destroy_instance():
    # TODO: Verify slug matches a regexp, at least.
    slug = request.form['slug']
    app.logger.info('attempting to destroy instance %s/%s on behalf of'
                    '%s.' % (g.project.id, slug, session['email']))
    g.project.destroy_instance(slug)
    flash('The instance <strong>%s</strong> has been scheduled for '
          'destruction, and will be removed shortly.' % escape(slug))
    return redirect('/%s/' % g.project.id)

@project_bp.route('/')
def project_index():
    instances = g.project.get_instances()
    for inst in instances:
        if inst['state'] == 'running' and 'url' not in inst:
            Thread(target=g.project.get_instance_status,
                   kwargs={'slug': inst['slug']}).run()
    return render_template('project.html',
                           project=g.project,
                           instances=instances)

app.register_blueprint(project_bp)

@app.route('/login', methods=['POST'])
def login():
    origin = "%(PREFERRED_URL_SCHEME)s://%(SERVER_NAME)s" % (app.config)
    data = browserid.verify(request.form['assertion'], origin)
    session['email'] = data['email']
    return data['email']

@app.route('/logout', methods=['POST'])
def logout():
    if 'email' in session:
        del session['email']
    return 'logged out'

@csrf_exempt
@app.route('/update', methods=['POST'])
def update():
    # TODO: Implement this.
    return 'update complete'

@app.route('/')
def index():
    projects = [Project(name) for name in get_project_map()]
    return render_template('index.html', projects=projects)
