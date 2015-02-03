"""

Mako Templates
--------------

Mako templating code was based on the code and discussion at
http://tools.cherrypy.org/wiki/Mako

To use the Mako renderer:
  cherrypy.tools.mako = cherrypy.Tool('on_start_resource',
                                      MakoLoader(directories=['/path/to/templates']))

Then in your handler:

    @cherrypy.tools.mako(filename='index.html')
    def index(self):
        return {}

"""
from mako.lookup import TemplateLookup
import cherrypy
try:
    import simplejson as json
except ImportError:
    import json

from pycrust import url

class MakoHandler(cherrypy.dispatch.LateParamPageHandler):
    """Callable which sets response.body."""

    def __init__(self, template, next_handler):
        self.template = template
        self.next_handler = next_handler

    def __call__(self):
        env = globals().copy()
        env.update(self.next_handler())

        ## Add any default session globals
        env.update({
            'session':  cherrypy.session,
            'url':      url,
        })

        return self.template.render_unicode(**env)


class MakoLoader(object):
    """Template loader for Mako"""

    def __init__(self, directories=[]):
        self.lookups = {}
        self.directories = directories

    def __call__(self, filename, directories=None, module_directory=None, collection_size=-1):

        if not directories:
            directories = self.directories

        # Find the appropriate template lookup.
        key = (tuple(directories), module_directory)
        try:
            lookup = self.lookups[key]
        except KeyError:
            lookup = TemplateLookup(directories=directories,
                                    module_directory=module_directory,
                                    collection_size=collection_size,
                                    input_encoding='utf-8',
                                    output_encoding='utf-8',
                                    encoding_errors='replace'
                                    )
            self.lookups[key] = lookup
        cherrypy.request.lookup = lookup

        # Replace the current handler.
        cherrypy.request.template = t = lookup.get_template(filename)
        cherrypy.request.handler = MakoHandler(t, cherrypy.request.handler)

