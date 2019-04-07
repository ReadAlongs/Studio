''' Run ReadAlong Studio as web application '''

import os
from readalongs.app import app

HOST = '0.0.0.0'
PORT = int(os.environ.get("PORT", 5000))
app.run(host=HOST, port=PORT, debug=True, threaded=True)
