#!/usr/bin/env python

""" Run ReadAlong Studio as web application

Define the PORT environment variable to specify which port to use (default: 5000).
"""

import os

from readalongs.app import app, socketio

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))
socketio.run(app, host=HOST, port=PORT, debug=True)
