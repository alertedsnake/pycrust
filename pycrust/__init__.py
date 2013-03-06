"""Pycrust

A collection of CherryPy extensions
"""

__author__ = 'Michael Stella <pycrust@thismetalsky.org>'
__version__ = '1.0.0'

import inspect, os
import routes
import cherrypy

class BaseHandler(object):
    """Base class for web handler objects"""
    _cp_config = {}

    def log(self, msg):
        """Logs to the Cherrypy error log but in a much more pretty way,
        with the handler name and line number
        """
        c = inspect.getouterframes(inspect.currentframe())[1]
        cherrypy.log.error(msg, context='HANDLER ({0}:{1})'.format(os.path.basename(c[1]), c[2]))


def url(*args, **kwargs):
    """Find the given URL using routes"""

    if 'absolute' in kwargs and kwargs['absolute']:
        return cherrypy.url(routes.url_for(*args, **kwargs))

    return routes.url_for(*args, **kwargs)


def dump_request(*args, **kwargs):
    """Dumps the request out to a file in /tmp, for debugging"""

    with open('/tmp/request.%s.txt' % cherrypy.request.method, 'w') as f:

        f.write(cherrypy.request.request_line)

        # write headers
        for (k,v) in cherrypy.request.headers.items():
            f.write('%s: %s\n' % (k,v))

        f.write("\n")

        # dump out the POST data when submitted
        if ('Content-Type' in cherrypy.request.headers and
                'application/x-www-form-urlencoded' in cherrypy.request.headers['Content-Type']):
            for (k,v) in cherrypy.request.params.items():
                f.write('%s: %s\n' % (k,v))

        # otherwise, dump the body
        elif cherrypy.request.body:
            with cherrypy.request.body.make_file() as fin:
                f.write(str(fin.read()))



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
            f.write(str(cherrypy.response.collapse_body()))

cherrypy.tools.debug_request  = cherrypy.Tool('on_end_resource', dump_request)
cherrypy.tools.debug_response = cherrypy.Tool('on_end_resource', dump_response)

