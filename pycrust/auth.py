"""
User authentication and authorization for CherryPy

This code is based on the examples and discussion at
http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions


"""

__author__ = 'Michael Stella <pycrust@thismetalsky.org>'

import cherrypy
from six.moves import urllib

from pycrust import url

def check_auth(*args, **kwargs):
    """Check authentication before each handler"""

    conditions = cherrypy.request.config.get('auth.require', None)
    if conditions:
        uid = cherrypy.session.get('uid')
        if uid:
            cherrypy.request.login = uid
            for c in conditions:
                if not c():
                    raise cherrypy.HTTPError(403)

        else:
            # throw a 401 rather than redirect if this is a JSON-wanting request
            # not sure why some things set HTTP_ACCEPT and others ACCEPT
            for h in ('ACCEPT', 'HTTP_ACCEPT'):
                if (h in cherrypy.request.headers and
                    'application/json' in cherrypy.request.headers[h]):
                    raise cherrypy.HTTPError(401)

            # otherwise, for a normal request,
            # redirect to the login page, preserving the 'return' URL
            target = url('login')
            referer = cherrypy.request.request_line.split()[1]
            if referer:
                target = "%s?ret=%s" % (target,  urllib.parse.quote(referer))
            raise cherrypy.HTTPRedirect(target)

cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)


## auth decorators
def require(*conditions):
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate

def all_of(*conditions):
    def check():
        for c in conditions:
            if not c():
                return False
        return True
    return check

def one_of(*conditions):
    def check():
        for c in conditions:
            if c():
                return True
        return False
    return check

## auth conditions
def auth_valid_user():
    """True if there is a user logged in"""
    def check():
        if cherrypy.request.login:
            return True
        return False
    return check

def auth_user(id):
    """True if the userid matches"""
    return lambda: cherrypy.request.login == id

