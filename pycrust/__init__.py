"""
Pycrust

A collection of CherryPy extensions

See also the following submodules:

    pycrust.auth
    pycrust.saplugin
    pycrust.satool
    pycrust.tools


"""

__author__ = 'Michael Stella <pycrust@thismetalsky.org>'
__version__ = '1.0.0'

import inspect, logging, os, sys
import cherrypy
import codecs

class BaseHandler(object):
    """A Base class for web handler objects."""
    _cp_config = {}

    def log(self, msg, severity=logging.INFO, context=None):
        """Logs to the Cherrypy error log but in a much more pretty way,
        with the handler name and line number
        """
        if not context:
            context = inspect.getouterframes(inspect.currentframe())[1]
        cherrypy.log.error(msg=msg.strip().replace('\n', '; '), severity=severity,
                           context='HANDLER ({}:{}:{})'.format(
                                self.__class__.__name__, context[3], context[2]))

    def log_debug(self, msg):
        return self.log(msg, severity=logging.DEBUG,
                        context=inspect.getouterframes(inspect.currentframe())[1])

    def log_info(self, msg):
        return self.log(msg, severity=logging.INFO,
                        context=inspect.getouterframes(inspect.currentframe())[1])

    def log_warn(self, msg):
        return self.log(msg, severity=logging.WARN,
                        context=inspect.getouterframes(inspect.currentframe())[1])

    def log_error(self, msg):
        return self.log(msg, severity=logging.ERROR,
                        context=inspect.getouterframes(inspect.currentframe())[1])

    def log_fatal(self, msg):
        return self.log(msg, severity=logging.FATAL,
                        context=inspect.getouterframes(inspect.currentframe())[1])


def url(*args, **kwargs):
    """Find the given URL using routes.  Throws an exception
    if you're not using routes.
    """

    import routes

    if 'absolute' in kwargs and kwargs['absolute']:
        del(kwargs['absolute'])
        return cherrypy.url(routes.url_for(*args, **kwargs))

    return routes.url_for(*args, **kwargs)


def dump_request(*args, **kwargs):
    """Dumps the request out to a file in /tmp, for debugging

    Enable by setting, in your config file:
        tools.debug_request.on  = True
    """

    with codecs.open('/tmp/request.%s.txt' % cherrypy.request.method, 'w', encoding='utf-8') as f:

        f.write(cherrypy.request.request_line)
        f.write("\n")

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
    """Dumps the response out to a file in /tmp, for debugging.

    Enable by setting, in your config file:
        tools.debug_response.on  = True
    """

    # when a 500 error is displayed, cherrypy handles this
    # differently, and we don't really need to dump it out
    if not cherrypy.response.status:
        return

    status = 200
    if isinstance(cherrypy.response.status, int):
        status = cherrypy.response.status
    elif isinstance(cherrypy.response.status, str):
        status = int(cherrypy.response.status.split(' ', 1)[0])

    with codecs.open('/tmp/response.%d.txt' % status, 'w', encoding='utf-8') as f:

        f.write("HTTP/1.1 %s\n" % cherrypy.response.status)
        for (k,v) in cherrypy.response.headers.items():
            f.write('%s: %s\n' % (k,v))
        f.write("Status: %d\n\n" % status)

        if cherrypy.response.body:
            if sys.version < '3':
                f.write(str(cherrypy.response.collapse_body().decode()))
            else:
                f.write(str(cherrypy.response.collapse_body()))


cherrypy.tools.debug_request  = cherrypy.Tool('before_handler', dump_request, priority=1)
cherrypy.tools.debug_response = cherrypy.Tool('on_end_resource', dump_response)


def load_class(fullname):
    """Loads a class given the full dotted class name"""
    assert fullname is not None, "fullname must not be None"
    modulename, classname = fullname.rsplit('.', 1)

    try:
        module = __import__(modulename, globals(), locals(), [classname])
    except ImportError as e:
        cherrypy.log("Error loading module {}".format(modulename), context='ENGINE', severity=loging.ERROR)
        raise

    try:
        cls = getattr(module, classname)
    except AttributeError as e:
        cherrypy.log("Error loading class {} from module {}".format(classname, modulename),
                      context='ENGINE', severity=logging.ERROR)
        return None

    return cls

