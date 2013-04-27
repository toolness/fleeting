import os
import re

from .utils import path

class Project(object):
    def __init__(self, name):
        pmap = get_project_map()
        self.name = name
        self.script_path = pmap[name]
        self.script_content = open(self.script_path, 'r').read()
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
