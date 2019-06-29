''' ReadAlong Studio App '''

from flask import Flask, session
from flask_session import Session
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "secret key"
# app.config['SESSION_PERMANENT'] = True
# app.config['SESSION_TYPE'] = 'filesystem'
# app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
# app.config['SESSION_FILE_THRESHOLD'] = 100

# sess = Session()
# sess.init_app(app)
import readalongs.views
