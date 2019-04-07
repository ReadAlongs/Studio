''' Run ReadAlong Studio as web application '''

import os
from readalong_studio import app

HOST = '0.0.0.0'
PORT = int(os.environ.get("PORT", 5000))
app.run(host=HOST, port=PORT, debug=True, threaded=True)
