from flask import Flask, Blueprint, abort, g, render_template

from .project import Project, get_project_map

app = Flask(__name__)

@app.after_request
def add_csp_headers(response):
    policy = "default-src 'self'"
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
    return 'TODO: implement this'

app.register_blueprint(project_bp)

@app.route('/update', methods=['POST'])
def update():
    # TODO: Implement this.
    return 'update complete'

@app.route('/')
def index():
    projects = [Project(name) for name in get_project_map()]
    return render_template('index.html', projects=projects)
