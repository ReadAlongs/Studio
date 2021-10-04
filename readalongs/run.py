#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#####################################################################################
#
# run.py
#
#   It seems Werkzeug doesn't play well with SocketIO, so use SocketIO to run the app
#   Watch this issue: https://github.com/miguelgrinberg/Flask-SocketIO/issues/894
#
#   This file might seem redundant with ../run.py, but it's not: this here is invoked
#   by "readalongs run", through click and Flask. Flask supplies the "run" command by
#   default, using Werkzeug by default, bug we provide our overriding implementation
#   here.
#
#   By contrast, ../run.py can be invoked directly to manually run the app on a
#   hard-coded port. This is also what is used by default in our Dockerfile.
#
######################################################################################

from readalongs.app import app, socketio


def run():
    """ Run app using SocketIO
    """
    socketio.run(app)


if __name__ == "__main__":
    run()
