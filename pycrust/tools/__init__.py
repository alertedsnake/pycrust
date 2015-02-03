"""
Extra tools/enhancements not included with Cherrypy

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
try:
    import simplejson as json
except ImportError:
    import json

from pycrust import url

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

