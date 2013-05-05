import os
from urllib import quote

from . import app, utils, project, tempcache

REQUIRED_KEYS = [
    'SECRET_KEY',
    'SERVER_NAME',
    'AWS_KEY_NAME',
    'AWS_SECURITY_GROUP',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY'
]

def force_preferred_url_scheme(wsgi_app):
    def wrapper(environ, start_response):
        SITE_SCHEME = app.config['PREFERRED_URL_SCHEME']

        # For some reason 'secure_scheme_headers' in gunicorn config
        # is failing us, so we'll do it manually here.
        osh = os.environ.get('ORIGINATING_SCHEME_HEADER')
        if osh:
            osh = 'HTTP_%s' % osh.replace('-', '_').upper()
            if environ.get(osh) == 'https':
                environ['wsgi.url_scheme'] = 'https'

        # If the SITE_URL is explicitly defined, then we're going to
        # force a redirect to the proper protocol (http or https)
        # if necessary.
        if environ['wsgi.url_scheme'] != SITE_SCHEME:
            url = '%s://%s' % (SITE_SCHEME, app.config['SERVER_NAME'])
            # http://www.python.org/dev/peps/pep-0333/#url-reconstruction
            url += quote(environ.get('SCRIPT_NAME', ''))
            url += quote(environ.get('PATH_INFO', ''))
            if environ.get('QUERY_STRING'):
                url += '?' + environ['QUERY_STRING']
            start_response("302 Found", [("Location", url)])
            return ["redirect to %s" % SITE_SCHEME]
        return wsgi_app(environ, start_response)
    return wrapper

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

    redis_url = os.environ.get('REDIS_URL', os.environ.get('REDISTOGO_URL'))
    if redis_url:
        app.logger.info('Using redis at %s.' % redis_url)
        project.cache = tempcache.RedisTempCache(
            project.DEFAULT_CACHE_TTL,
            url=redis_url
        )
    app.wsgi_app = force_preferred_url_scheme(app.wsgi_app)


init()
