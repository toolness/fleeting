import os
import re

from flask import Flask, Blueprint, abort, g

app = Flask(__name__)

ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *x: os.path.join(ROOT, *x)

project_bp = Blueprint('project', __name__, url_prefix='/<project>')

class Project(object):
    def __init__(self, name, script_path):
        self.name = name
        self.script_path = script_path
        self.script_content = open(script_path, 'r').read()
        self.meta = {}

        for line in self.script_content.splitlines():
            match = re.search(r'fleeting-meta:([a-z0-9\-]+)\s*=(.*)', line)
            if match:
                self.meta[match.group(1)] = match.group(2).strip()

def get_project_map():
    pmap = {}
    projects_dir = path('projects')
    for filename in os.listdir(projects_dir):
        if not filename.startswith('.'):
            abspath = os.path.join(projects_dir, filename)
            pmap[os.path.splitext(filename)[0]] = abspath
    return pmap

@project_bp.url_value_preprocessor
def pull_project(endpoint, values):
    pname = values.pop('project', None)
    pmap = get_project_map()
    if pname not in pmap:
        abort(404)
    g.project = Project(pname, pmap[pname]) 

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
    return ' '.join(get_project_map().keys())

if __name__ == '__main__':
    app.run(debug=True)
