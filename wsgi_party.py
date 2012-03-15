# -*- coding: utf-8 -*-
"""
    Partyline dispatcher for WSGI with good intentions.

    :copyright: (c) 2012 by Ron DuPlain.
    :license: BSD, see LICENSE for more details.
"""

from werkzeug.test import create_environ, run_wsgi_app


class WSGIParty(object):
    """Dispatcher for cross-application communication.

    Originally based on :class:`~werkzeug.wsgi.DispatcherMiddleware`.
    """

    #: URL path to the registration URL of participating applications.
    invite_path = '/__invite__/'

    #: Key in environ with reference to this dispatcher.
    partyline_key = 'partyline'

    def __init__(self, app, mounts=None, base_url=None):
        #: Application mounted at root.
        self.app = app

        #: Applications mounted at sub URLs, with sub-URL as the key.
        self.mounts = mounts or {}

        #: Base URL for use in environ. Defaults to None.
        self.base_url = base_url

        #: A list of participating applications.
        self.partyline = []

        self.send_invitations()

    def __call__(self, environ, start_response):
        """Dispatch WSGI call to a mounted application, default to root app."""
        # TODO: Consider supporting multiple applications mounted at root URL.
        #       Then, consider providing priority of mounted applications.
        #       One application could explicitly override some routes of other.
        script = environ.get('PATH_INFO', '')
        path_info = ''
        while '/' in script:
            if script in self.mounts:
                app = self.mounts[script]
                break
            items = script.split('/')
            script = '/'.join(items[:-1])
            path_info = '/%s%s' % (items[-1], path_info)
        else:
            app = self.mounts.get(script, self.app)
        original_script_name = environ.get('SCRIPT_NAME', '')
        environ['SCRIPT_NAME'] = original_script_name + script
        environ['PATH_INFO'] = path_info
        return app(environ, start_response)

    def send_invitations(self):
        """Call each application via our partyline connection protocol."""
        environ = create_environ(path=self.invite_path, base_url=self.base_url)
        environ[self.partyline_key] = self
        for application in self.applications:
            # TODO: Verify/deal with 404 responses from the application.
            run_wsgi_app(application, environ)

    @property
    def applications(self):
        """A list of all mounted applications, matching our protocol or not."""
        return [self.app] + self.mounts.values()

    def connect(self, application):
        """Connect application to the partyline for cross-app communication."""
        self.partyline.append(application)


class PartylineException(Exception):
    """Base exception class for wsgi_party."""


class AlreadyJoinedParty(PartylineException):
    """For bootstrapping."""


class PartylineConnector(object):
    """Mixin for registration & message passing."""

    #: The partyline_key set in :class:`WSGIParty`.
    partyline_key = 'partyline'

    def join_party(self, environ):
        """Mount this view function at '/__invite__/' script path."""
        try:
            # Provide a bootstrapping hook for the partyline.
            self.before_partyline_join(environ)
        except AlreadyJoinedParty:
            # Do not participate once bootstrapped.
            return
        if hasattr(self, 'on_partyline_join'):
            # Provide a hook when joining the partyline.
            self.on_partyline_join(environ)
        # Partyline dispatcher loads itself into the environ.
        self.partyline = environ.get(self.partyline_key)
        # Every participating application registers itself.
        self.partyline.connect(self)
        # Return something.
        return 'Hello, world!'

    def before_partyline_join(self, environ):
        """Connect to partyline or raise an exception."""
        if getattr(self, 'connected_partyline', False):
            raise AlreadyJoinedParty()
        self.connected_partyline = True
