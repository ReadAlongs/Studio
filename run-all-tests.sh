#!/bin/bash

# Run all tests locally, with all supported versions of Python
# Requires uv

# Python 3.9 no longer works with the latest hatch version, so do it by itself
RC=0
UV_PROJECT_ENVIRONMENT=.venv-py39 uv run --python 3.9 --dev pytest || RC=1

# Python 3.10 and more recent are all done by hatch matrix testing
HATCH_FAIL=
uvx hatch test -a || RC=1

exit $RC
