#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#####################################################################################
#
# run.py
#
#   It seems Werkzeug doesn't play well with SocketIO, so use SocketIO to run the app
#   Watch this issue: https://github.com/miguelgrinberg/Flask-SocketIO/issues/894
#
######################################################################################

from readalongs.app import app, socketio

def run():
    ''' Run app using SocketIO
    '''
    socketio.run(app)

if __name__ == "__main__":
    run()
