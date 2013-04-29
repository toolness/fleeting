import os

from . import app, utils

REQUIRED_KEYS = [
    'SECRET_KEY',
    'SERVER_NAME',
    'AWS_KEY_NAME',
    'AWS_SECURITY_GROUP',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY'
]

def init():
    utils.ensure_env_vars(REQUIRED_KEYS)

    app.config.update(
        SECRET_KEY=os.environ['SECRET_KEY'],
        SERVER_NAME=os.environ['SERVER_NAME'],
        PREFERRED_URL_SCHEME=os.environ.get('SERVER_SCHEME', 'http'),
    )

    import logging

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    app.logger.info('Server name is %s.' % app.config['SERVER_NAME'])

init()
