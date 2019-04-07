''' ReadAlong Studio App '''

from flask import Flask

VERSION = '0.0.1'

logger = getLogger('root')

app = Flask(__name__)

import readalong_studio.views
