from flask import Flask, Blueprint, abort, g

from . import project

app = Flask(__name__)

project_bp = Blueprint('project', __name__, url_prefix='/<project>')

@project_bp.url_value_preprocessor
def pull_project(endpoint, values):
    pname = values.pop('project', None)
    pmap = project.get_project_map()
    if pname not in pmap:
        abort(404)
    g.project = project.Project(pname, pmap[pname]) 

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
    # TODO: Link to project pages.
    return ' '.join(project.get_project_map().keys())
