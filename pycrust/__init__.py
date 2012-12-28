"""Pycrust

A collection of CherryPy extensions
"""

__author__ = 'Michael Stella <michael@thismetalsky.org>'
__version__ = '1.0.0'

import routes
import cherrypy

class BaseHandler(object):
    """Base class for web handler objects"""
    _cp_config = {}


def url(*args, **kwargs):
    """Find the given URL using routes"""
    if 'absolute' in kwargs and kwargs['absolute']:
        return cherrypy.url(routes.url_for(*args, **kwargs))

    return routes.url_for(*args, **kwargs)


def dump_request(*args, **kwargs):
    """Dumps the request out to a file in /tmp, for debugging"""
    with open('/tmp/request.%s.txt' % cherrypy.request.method, 'w') as f:

        f.write(cherrypy.request.request_line)

        for (k,v) in cherrypy.request.headers.items():
            f.write('%s: %s\n' % (k,v))

        if cherrypy.request.body:
            with cherrypy.request.body.make_file() as fin:
                f.write(fin.read())


def dump_response(*args, **kwargs):
    """Dumps the response out to a file in /tmp, for debugging"""

    # when a 500 error is displayed, cherrypy handles this
    # differently, and we don't really need to dump it out
    if not cherrypy.response.status:
        return

    status = 200
    if isinstance(cherrypy.response.status, int):
        status = cherrypy.response.status
    elif isinstance(cherrypy.response.status, str):
        status = int(cherrypy.response.status.split(' ', 1)[0])

    with open('/tmp/response.%d.txt' % status, 'w') as f:

        f.write("HTTP/1.1 %s\n" % cherrypy.response.status)
        for (k,v) in cherrypy.response.headers.items():
            f.write('%s: %s\n' % (k,v))
        f.write("Status: %d\n\n" % status)

        if cherrypy.response.body:
            f.write(cherrypy.response.collapse_body())

cherrypy.tools.debug_request  = cherrypy.Tool('on_end_resource', dump_request)
cherrypy.tools.debug_response = cherrypy.Tool('on_end_resource', dump_response)

