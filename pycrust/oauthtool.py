"""
OAuth1 tool.

NOTE: Currently this works in Python 3.x only, feel free to backport it.

Configuration:

    required settings;
        tools.oauth.realm = 'http://localhost/'

    optional settings:
        tools.oauth.request_token_url = '/oauth1/request_token'
        tools.oauth.access_token_url  = '/oauth1/access_token'
        tools.oauth.datastore.class   = 'pycrust.oauth.OAuthDataStore'

You really should override tools.oauth.datastore.class if you want
this to work :)

This work was based loosely on the oauthtool.py in the python-gearshift
project: https://code.google.com/p/python-gearshift/

"""

import cherrypy, logging
from six.moves import urllib

from pycrust import load_class, oauth

class OAuthTool(cherrypy.Tool):
    def __init__(self, app=''):
        """Optional argument 'app' will cause this to read
        the config from only the app in question, and base all
        paths on it"""

        # the config is a little buried, annoyingly
        config = cherrypy.tree.apps[app].config['/']

        self.realm                = config.get('tools.oauth.realm')
        self.o1_request_token_url = app + config.get('tools.oauth.request_token.url', '/oauth1/request_token')
        self.o1_access_token_url  = app + config.get('tools.oauth.access_token.url', '/oauth1/access_token')
        ds_classname              = config.get('tools.oauth.datastore.class', 'pycrust.oauth.OAuthDataStore')

        # load datastore class
        ds_class = load_class(ds_classname)
        if not callable(ds_class):
            raise TypeError("datastore class '{}' is not callable".format(ds_classname))
        self.datastore = ds_class(app=app)
        cherrypy.log(" Loaded auth datastore class {}".format(ds_classname),
                        context='ENGINE', severity=logging.INFO)

        self.oauth_server = oauth.OAuthServer(self.datastore)
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())

        cherrypy.log("OAuthTool initialized", context='ENGINE', severity=logging.INFO)

        super().__init__(point='before_handler', callable=self.before_handler, priority=10)


    def _setup(self):
        super()._setup()
        cherrypy.request.hooks.attach(point='before_finalize', callback=self.before_finalize)


    def send_oauth_error(self, msg, code=401):
        header = oauth.build_authenticate_header(realm=self.realm)
        for k, v in header.items():
            cherrypy.response.headers[k] = v

        cherrypy.log(msg, context='ENGINE', severity=logging.INFO)
        raise cherrypy.HTTPError(code)


    def before_handler(self, **kwargs):
        from_request = oauth.OAuthRequest.from_request
        headers = cherrypy.request.headers.copy()

        params = urllib.parse.parse_qs(cherrypy.request.query_string)
        if cherrypy.request.body_params:
            params.update(cherrypy.request.body_params)

        # figure out the real URL
        host = cherrypy.request.headers.get("X-Forwarded-Host") or cherrypy.request.headers.get("Host")
        url = "{}://{}{}{}".format(
                    cherrypy.request.scheme,
                    host,
                    cherrypy.request.script_name,
                    cherrypy.request.path_info)

        oauth_request = from_request(
                http_method=cherrypy.request.method,
                http_url=url,
                headers=headers,
                parameters=params,
                query_string=cherrypy.request.query_string,
            )

        # nothing for us to do here
        if not oauth_request or not 'oauth_consumer_key' in oauth_request.parameters:
            return

        cherrypy.request.oauth_request = oauth_request
        cherrypy.request.oauth_server = self.oauth_server

        # Remove any oauth-related params from the request, so that
        # those params don't get passed around and confuse handlers.
        for key in list(cherrypy.request.params.keys()):
            if key.startswith('oauth_'):
                del(cherrypy.request.params[key])

        uri = cherrypy.request.script_name + cherrypy.request.path_info

        # this is an OAuth1 request token request
        if uri == self.o1_request_token_url:

            try:
                # create a request token
                token = self.oauth_server.fetch_request_token(oauth_request)
            except oauth.OAuthError as e:
                return self.send_oauth_error("auth request error: {}".format(e.message))

            # Tell CherryPy that we have processed the request
            tokstr = token.to_string()
            if not isinstance(tokstr, bytes):
                tokstr = tokstr.encode('utf-8')
            cherrypy.response.body = [tokstr]
            cherrypy.request.handler = None

            # Delete Content-Length header so finalize() recalcs it.
            cherrypy.response.headers.pop("Content-Length", None)

        # this is an OAuth1 access token request
        elif uri == self.o1_access_token_url:
            try:
                token = self.oauth_server.fetch_access_token(oauth_request)
            except oauth.OAuthError as e:
                return self.send_oauth_error("auth token error: {}".format(e.message))

            tokstr = token.to_string()
            if not isinstance(tokstr, bytes):
                tokstr = tokstr.encode('utf-8')
            cherrypy.response.body = [tokstr]
            cherrypy.request.handler = None
            cherrypy.response.headers.pop("Content-Length", None)


    def before_finalize(self, **kwargs):
        # Even if we have an oauth_request, that doesn't mean it's valid
        oauth_request = getattr(cherrypy.request, 'oauth_request', None)


