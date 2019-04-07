''' ReadAlong Studio App '''

from flask import Flask

app = Flask(__name__)

import readalongs.views
