
import datetime
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

        return self.template.render(**env)


class MakoLoader(object):

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
    return json.dumps(value, sort_keys=True, indent=4, cls=JSONCustomEncoder)


class JSONCustomEncoder(json.JSONEncoder):
    """Custom JSON encoder class"""
    def default(self, obj):
        if hasattr(obj, '__to_json__'):
            return obj.__to_json__()
        if hasattr(obj, '__to_dict__'):
            return obj.__to_dict__()

        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.strftime('%s')

        return json.JSONEncoder.default(self, obj)

