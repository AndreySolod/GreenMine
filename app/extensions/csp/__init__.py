from flask import Flask, g, Blueprint
from typing import Optional
from flask import request
import secrets


class CSPNonce:
    def generate(self):
        """ generate nonce - random value and save him at g """
        if 'CSP_NONCE' in g:
            return g.CSP_NONCE
    def __str__(self):
        if 'CSP_NONCE' in g:
            return g.CSP_NONCE
        return 'CSPNonce <None>'


class CSPNonceSecrets(CSPNonce):
    """ CSP Nonce class to generate him via secrets library """
    def generate(self):
        nonce = super(CSPNonceSecrets, self).generate()
        if nonce is not None:
            return nonce
        g.CSP_NONCE = secrets.token_urlsafe()
        return g.CSP_NONCE


DEFAULT_POLICY = {"script-src": CSPNonceSecrets(), "img-src": "'self' data:", "child-src": "", "default-src": "'self'",
                  "plugin-src": "", "style-src": "'self' 'unsafe-inline'", "media-src": "", "object-src": "", "connect-src": "",
                  "worker-src": "'self' blob:", "base-uri": ""}
# "report-uri": "/csp_report"
# https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
# https://github.com/twaldear/flask-csp/blob/master/flask_csp/csp.py


def csp_nonce():
    if 'CSP_NONCE' in g:
        return g.CSP_NONCE
    return None


class CSPManager:
    def __init__(self, app: Optional[Flask]=None, policy: Optional[dict[str, str]]=DEFAULT_POLICY, report_uri: Optional[str]=None):
        self.exempt_views = set()
        self.exempt_blueprints = set()
        for keys, values in policy.items():
            if values == 'self':
                policy[keys] = "'self'"
        self.policy = policy
        if report_uri:
            self.policy.setdefault('report-uri', report_uri)
        if app:
            self.init_app(app)
    
    def get_csp_headers(self):
        ''' function to create csp headers '''
        policy_list = []
        for k, v in self.policy.items():
            if v != '' and isinstance(v, str):
                policy_list += [f"{k} {v}"]
            elif isinstance(v, CSPNonceSecrets):
                policy_list += [f"{k} 'nonce-{v.generate()}'"]
            elif isinstance(v, list):
                policy_list += [f"{k} " + " ".join([str(i) for i in v])]
        return '; '.join(policy_list)
    
    def init_app(self, app: Flask):
        app.jinja_env.globals['csp_nonce'] = csp_nonce
        app.config.setdefault("CSP_ENABLED", True)

        @app.before_request
        def create_request_policy():
            self.get_csp_headers()
        
        @app.after_request
        def set_request_policy(response):
            if not app.config["CSP_ENABLED"]:
                return response

            if not request.endpoint: # TODO: ERROR: CSP is violated when using an iframe!
                return response

            if app.blueprints.get(request.blueprint) in self.exempt_blueprints:
                return response

            view = app.view_functions.get(request.endpoint)
            dest = f"{view.__module__}.{view.__name__}"

            if dest in self.exempt_views:
                return response
            response.headers['Content-Security-Policy'] = self.get_csp_headers()
            return response
        
        def extempt(self, view):
            """ Mark a view or blueprint to be excluded from CSP protection
            
            @app.route('/index')
            @csp.extempt
            def some_view():
                ...
            
            bp = Blueprint(...)
            csp.extempt(bp)
            """
            if isinstance(view, Blueprint):
                self.exempt_blueprints.add(view)
                return view
            if isinstance(view, str):
                view_location = view
            else:
                view_location = ".".join((view.__module__, view.__name__))
            self.exempt_views.add(view_location)
            return view