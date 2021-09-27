#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# app.py
#
#   Initializes a Flask web application with
#   session manager and SocketIO integration.
#
#######################################################################

import os

from flask import Flask
from flask_socketio import SocketIO

from flask_session import Session
from readalongs.python_version import ensure_using_supported_python_version

ensure_using_supported_python_version()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
socketio = SocketIO(app, manage_session=False)

import readalongs.views  # noqa: E402
