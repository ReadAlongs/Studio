#!/usr/bin/env python3

""" Run ReadAlong Studio as web application """

import os
from readalongs.app import app, socketio

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))
socketio.run(app, host=HOST, port=PORT, debug=True)
