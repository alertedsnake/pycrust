"""User authentication and authorization for CherryPy"""

import cherrypy
import urllib

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

        # redirect to the login page, preserving the 'return' URL
        else:
            target = url('login')
            referer = cherrypy.request.request_line.split()[1]
            if referer:
                target = "%s?ret=%s" % (target,  urllib.quote(referer))
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

