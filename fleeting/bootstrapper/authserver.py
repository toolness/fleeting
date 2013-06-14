import sys
from base64 import b64encode
from wsgiref.simple_server import make_server

from webob.static import DirectoryApp
from webob.dec import wsgify
from webob.exc import HTTPUnauthorized

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print "usage: %s <port> <dirname> <user:pass>" % sys.argv[0]
        sys.exit(1)

    port = int(sys.argv[1])
    dirname = sys.argv[2]
    creds = sys.argv[3]
    b64_creds = b64encode(creds)

    dirapp = DirectoryApp(dirname)

    @wsgify
    def password_protected_app(req):
        if req.authorization == ('Basic', b64_creds):
            return dirapp

        response = HTTPUnauthorized()
        response.www_authenticate = ('Basic', dict(realm='authserver'))
        return response

    httpd = make_server('', port, password_protected_app)
    httpd.serve_forever()
