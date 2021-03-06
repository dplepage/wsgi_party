# -*- coding: utf-8 -*-
"""
    Partyline middleware for WSGI with good intentions.

    :copyright: (c) 2012 by Ron DuPlain.
    :license: BSD, see LICENSE for more details.
"""

from werkzeug.test import create_environ, run_wsgi_app


class PartylineException(Exception):
    """Base exception class for wsgi_party."""


class HighAndDry(PartylineException):
    """Handler does not have a response; skip it."""


class PartylineOperator(object):
    """Expose an API for connecting a listener to the WSGI partyline.

    The WSGI application uses this object to communicate with the party, with
    one operator per invitation, and typically one invitation per WSGI
    application.  One operator per application prevents an application from
    handling a request from itself.
    """

    def __init__(self, partyline):
        self.partyline = partyline
        self.handlers = set()

    def connect(self, service_name, handler):
        self.handlers.add(handler)
        return self.partyline.connect(service_name, handler)

    def ask_around(self, service_name, payload):
        return self.partyline.ask_around(self, service_name, payload)


class WSGIParty(object):
    """Partyline middleware WSGI object."""

    #: Key in environ with reference to the partyline operator.
    partyline_key = 'partyline'

    #: Class to use as the partyline operator, for connecting listeners.
    operator_class = PartylineOperator

    def __init__(self, application, invites=()):
        #: Wrapped WSGI application.
        self.application = application

        #: A dict of service name -> handler mappings.
        self.handlers = {}

        self.send_invitations(invites)

    def __call__(self, environ, start_response):
        """Call wrapped application."""
        return self.application(environ, start_response)

    def send_invitations(self, invites):
        """Call each invite route to establish a partyline."""
        for invite in invites:
            environ = create_environ(path=invite)
            environ[self.partyline_key] = self.operator_class(self)
            run_wsgi_app(self.application, environ)

    def connect(self, service_name, handler):
        """Register a handler for a given service name."""
        self.handlers.setdefault(service_name, []).append(handler)

    def ask_around(self, operator, service_name, payload):
        """Notify all listeners of a service name and yield their results."""
        for handler in self.handlers[service_name]:
            if handler in operator.handlers:
                # Skip handlers on the same operator, ask *others* for answer.
                continue
            try:
                yield handler(payload)
            except HighAndDry:
                continue
