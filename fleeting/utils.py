import os
from urllib import quote

ROOT = os.path.dirname(os.path.abspath(__file__))

path = lambda *x: os.path.join(ROOT, *x)

def ensure_env_vars(vars):
    for key in vars:
        if not key in os.environ:
            raise KeyError('environment variable %s is not defined' % key)

def force_preferred_url_scheme(app, originating_scheme_header=None):
    wsgi_app = app.wsgi_app
    osh = originating_scheme_header
    if osh:
        osh = 'HTTP_%s' % osh.replace('-', '_').upper()

    def force_preferred_url_scheme_middleware(environ, start_response):
        site_scheme = app.config['PREFERRED_URL_SCHEME']

        if osh and environ.get(osh) == 'https':
            environ['wsgi.url_scheme'] = 'https'

        # If the SITE_URL is explicitly defined, then we're going to
        # force a redirect to the proper protocol (http or https)
        # if necessary.
        if environ['wsgi.url_scheme'] != site_scheme:
            url = '%s://%s' % (site_scheme, app.config['SERVER_NAME'])
            # http://www.python.org/dev/peps/pep-0333/#url-reconstruction
            url += quote(environ.get('SCRIPT_NAME', ''))
            url += quote(environ.get('PATH_INFO', ''))
            if environ.get('QUERY_STRING'):
                url += '?' + environ['QUERY_STRING']
            start_response("302 Found", [("Location", url)])
            return ["redirect to %s" % site_scheme]
        return wsgi_app(environ, start_response)

    app.wsgi_app = force_preferred_url_scheme_middleware
