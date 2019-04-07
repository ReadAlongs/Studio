''' ReadAlong Studio App '''

from flask import Flask
from flask_talisman import Talisman, GOOGLE_CSP_POLICY
import os
from logging.config import dictConfig
from logging import getLogger

VERSION = '0.0.1'

logger = getLogger('root')

app = Flask(__name__)

import readalong_studio.views