"""
Extra tools/enhancements not included with Cherrypy

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


JSON Output
-----------

The JSON output handler here allows you to convert arbitrary obects
into JSON format, and send them out as a application/json response.

This method uses a custom encoder, and calls obj.__to_json__() or
obj.__to_dict__() on any object which has this method.  This method
should return the data in the object as a dict.


"""

__author__ = 'Michael Stella <pycrust@thismetalsky.org>'

import datetime
import sys

import cherrypy
from mako.lookup import TemplateLookup
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


#### JSON Output ####

def json_handler(*args, **kwargs):
    """Custom JSON handler which uses the custom encoder"""
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)

    # optionally set indent=4 here
    out = json.dumps(value, sort_keys=True, cls=JSONCustomEncoder, allow_nan=False)

    # Cherrypy wants us to return bytes, so in Python 3 we have to
    # encode the JSON output properly
    if sys.version < '3':
        return out
    else:
        return bytes(out , 'utf-8')


class JSONCustomEncoder(json.JSONEncoder):
    """Custom JSON encoder class"""
    def default(self, obj):
        if hasattr(obj, '__to_json__'):
            return obj.__to_json__()
        if hasattr(obj, '__to_dict__'):
            return obj.__to_dict__()

        # we convert dates into ISO format, it's reasonably portable
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)

