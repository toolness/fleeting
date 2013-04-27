import os

ROOT = os.path.dirname(os.path.abspath(__file__))

path = lambda *x: os.path.join(ROOT, *x)
