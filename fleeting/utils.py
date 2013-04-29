import os

ROOT = os.path.dirname(os.path.abspath(__file__))

path = lambda *x: os.path.join(ROOT, *x)

def ensure_env_vars(vars):
    for key in vars:
        if not key in os.environ:
            raise KeyError('environment variable %s is not defined' % key)
