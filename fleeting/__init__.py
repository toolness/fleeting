from flask import Flask, Blueprint, abort, g, render_template

from . import project

app = Flask(__name__)

project_bp = Blueprint('project', __name__, url_prefix='/<project>')

@project_bp.url_value_preprocessor
def pull_project(endpoint, values):
    pname = values.pop('project', None)
    if pname not in project.get_project_map():
        abort(404)
    g.project = project.Project(pname)

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
    projects = project.get_project_map().keys()
    return render_template('index.html', projects=projects)
