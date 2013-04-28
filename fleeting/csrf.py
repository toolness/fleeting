# -*- coding: utf-8 -*-
"""
    flaskext.csrf
    ~~~~~~~~~~~~~

    A small Flask extension for adding CSRF protection.

    :copyright: (c) 2010 by Steve Losh.
    :license: MIT, see LICENSE for more details.

    Customizations were made to this file by Atul Varma.
"""

from uuid import uuid4
from flask import abort, request, session, g

_exempt_views = []

def csrf_exempt(view):
    _exempt_views.append(view)
    return view

def enable_csrf(app):
    @app.before_request
    def _csrf_check_exemptions():
        dest = app.view_functions.get(request.endpoint)
        g._csrf_exempt = dest in _exempt_views
    
    @app.before_request
    def _csrf_protect():
        if not g._csrf_exempt:
            if request.method == "POST":
                csrf_token = session.get('_csrf_token', None)
                if (not csrf_token or
                    csrf_token != request.form.get('_csrf_token')):
                    abort(400)
    
    def generate_csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = str(uuid4())
        return session['_csrf_token']
    
    app.jinja_env.globals['csrf_token'] = generate_csrf_token
