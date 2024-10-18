#!/bin/bash

# Convenience script to launch the Web API in development mode.
# Do not use in production!  (See ../Procfile for the prod launch command.)
#
# Usage:
#    pip install uvicorn
#    /path/to/run-web-api.sh
#
# Further documentation is in readalongs/web_api.py

# Move to the code root directory, so that --reload works correctly.
CODE_ROOT_PATH=$(dirname $(realpath $0))/readalongs
cd $CODE_ROOT_PATH

# Launch the Web API with the --reload option, which will automatically reload
# the server whenver the code changes.
DEVELOPMENT=1 uvicorn readalongs.web_api:web_api_app --reload
