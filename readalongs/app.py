''' ReadAlong Studio App '''
import os
from flask import Flask, session
from flask_session import Session
from flask_login import LoginManager
from flask_socketio import SocketIO
from datetime import timedelta



app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app, manage_session=False)

import readalongs.views
