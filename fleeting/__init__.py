import os

import browserid
from flask import Flask, Blueprint, abort, g, render_template, request, \
                  session
from .csrf import enable_csrf, csrf_exempt

from .project import Project, get_project_map

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

enable_csrf(app)

app.jinja_env.globals['email'] = lambda: session.get('email', '')

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

@project_bp.route('/')
def project_index():
    return render_template('project.html', project=g.project)

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
