"""
OAuth1 tool.

NOTE: Currently this has only been tested thoroughly in Python 3.

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
project: https://code.google.com/p/python-gearshift/ which is licensed
under the MIT license, please see LICENSE.gearshift for details.

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

        self.realm              = config.get('tools.oauth.realm')
        self.request_token_url  = app + config.get('tools.oauth.request_token.url',    '/oauth1/request_token')
        self.access_token_url   = app + config.get('tools.oauth.access_token.url',     '/oauth1/access_token')
        ds_classname            = config.get('tools.oauth.datastore.class', 'pycrust.oauth.OAuthDataStore')

        # load datastore class
        ds_class = load_class(ds_classname)
        if not callable(ds_class):
            raise TypeError("datastore class '{}' is not callable".format(ds_classname))
        self.datastore = ds_class(app=app)
        cherrypy.log("OAuthTool loaded auth datastore class {}".format(ds_classname),
                        context='ENGINE', severity=logging.INFO)

        self.oauth_server = oauth.OAuthServer(self.datastore)
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())

        cherrypy.log("OAuthTool initialized", context='ENGINE', severity=logging.INFO)

        super().__init__(point='before_handler', callable=self.before_handler, priority=10)


    def send_oauth_error(self, msg, code=401):
        header = oauth.build_authenticate_header(realm=self.realm)
        for k, v in header.items():
            cherrypy.response.headers[k] = v

        cherrypy.log("OAuthTool " + msg, context='ENGINE', severity=logging.INFO)
        raise cherrypy.HTTPError(code)


    def before_handler(self, **kwargs):
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

        oauth_request = oauth.OAuthRequest.from_request(
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
        if uri == self.request_token_url:

            try:
                # create a request token
                token = self.oauth_server.fetch_request_token(oauth_request)
            except oauth.OAuthError as e:
                return self.send_oauth_error("request error: {}".format(e.message))

            # Tell CherryPy that we have processed the request
            tokstr = token.to_string()
            if not isinstance(tokstr, bytes):
                tokstr = tokstr.encode('utf-8')
            cherrypy.response.body = [tokstr]
            cherrypy.request.handler = None

            # Delete Content-Length header so finalize() recalcs it.
            cherrypy.response.headers.pop("Content-Length", None)

        # this is an OAuth1 access token request
        elif uri == self.access_token_url:
            try:
                token = self.oauth_server.fetch_access_token(oauth_request)
            except oauth.OAuthError as e:
                return self.send_oauth_error("auth error: {}".format(e.message))

            tokstr = token.to_string()
            if not isinstance(tokstr, bytes):
                tokstr = tokstr.encode('utf-8')
            cherrypy.response.body = [tokstr]
            cherrypy.request.handler = None
            cherrypy.response.headers.pop("Content-Length", None)


class OAuth2Tool(cherrypy.Tool):
    def __init__(self, app=''):
        """Optional argument 'app' will cause this to read
        the config from only the app in question, and base all
        paths on it"""

        # the config is a little buried, annoyingly
        config = cherrypy.tree.apps[app].config['/']

        self.realm          = config.get('tools.oauth.realm')
        self.token_url      = app + config.get('tools.oauth2.oauth_token_url',     '/oauth2/token')
        self.authorize_url  = app + config.get('tools.oauth2.oauth_authorize_url', '/oauth2/authorize')
        ds_classname        = config.get('tools.oauth.datastore.class', 'pycrust.oauth.OAuthDataStore')

        # load datastore class
        ds_class = load_class(ds_classname)
        if not callable(ds_class):
            raise TypeError("datastore class '{}' is not callable".format(ds_classname))
        self.datastore = ds_class(app=app)
        cherrypy.log("OAuth2Tool loaded auth datastore class {}".format(ds_classname),
                        context='ENGINE', severity=logging.INFO)

        self.oauth_server = oauth.OAuth2Server(self.datastore)
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())

        cherrypy.log("OAuth2Tool initialized", context='ENGINE', severity=logging.INFO)

        super().__init__(point='before_handler', callable=self.before_handler, priority=10)


    def send_oauth_error(self, msg, code=401):
        header = oauth.build_authenticate_header(realm=self.realm)
        for k, v in header.items():
            cherrypy.response.headers[k] = v

        cherrypy.log("OAuth2Tool error: " + msg, context='ENGINE', severity=logging.INFO)
        raise cherrypy.HTTPError(code, msg)


    def before_handler(self, **kwargs):
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

        uri = cherrypy.request.script_name + cherrypy.request.path_info
        if uri == self.authorize_url:
            if not 'response_type' in params or params['response_type'][0] != 'code':
                self.send_oauth_error("Invalid or missing parameter 'response_type'", 404)

            oauth_request = oauth.OAuth2Request.from_request(
                    http_method=cherrypy.request.method,
                    http_url=url,
                    headers=headers,
                    parameters=params,
                    query_string=cherrypy.request.query_string,
                )

            try:
                token = self.oauth_server.fetch_request_token(oauth_request)
            except oauth.OAuthError as e:
                return self.send_oauth_error("request error: {}".format(e.message))

            # client might be redirected to a local auth server
            if 'redirect_uri' in params:
                target_url = params['redirect_uri']
            else:
                target_url = self.token_url

            # generate a 302 response
            rsp = target_url + '?code={}'.format(token.key)
            if 'state' in params:
                rsp += '&state={}'.format(params['state'])
            if 'scope' in params:
                rsp += '&scope={}'.format(params['scope'])

            raise cherrypy.HTTPRedirect(rsp, 302)


        elif uri == self.token_url:

            oauth_request = oauth.OAuth2Request.from_request(
                    http_method=cherrypy.request.method,
                    http_url=url,
                    headers=headers,
                    parameters=params,
                    query_string=cherrypy.request.query_string,
                )

            grant_type = oauth_request.get_parameter('grant_type')

            token = None
            if grant_type == 'authorization_code':
                try:
                    token = self.oauth_server.fetch_access_token(oauth_request)
                except oauth.OAuthError as e:
                    return self.send_oauth_error("authorization_code auth error: {}".format(e.message))

            elif grant_type == 'client_credentials':
                try:
                    token = self.oauth_server.authenticate_client_credentials(oauth_request)
                except oauth.OAuthError as e:
                    return self.send_oauth_error("client_credentials auth error: {}".format(e.message))

            else:
                return self.send_oauth_error("bad value for grant_type")

            # return this as JSON rather than an encoded query string,
            # so we can easily parse it with Google's java oauth library.
            tokstr = token.to_json2()
            if not isinstance(tokstr, bytes):
                tokstr = tokstr.encode('utf-8')
            cherrypy.response.body = [tokstr]

            # Tell CherryPy that we have processed the request
            cherrypy.request.handler = None
            cherrypy.response.headers.pop("Content-Length", None)


