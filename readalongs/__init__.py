"""
Root module for the readalongs text/audio aligner.

Version for setuptools is changed here
Minimum Python version requirements is also validated here

The command line interface is defined in readalongs.cli.
The main alignment module is readalongs.align.
"""

import sys

if sys.version_info < (3, 8, 0):  # pragma: no cover
    sys.exit(
        f"Python 3.8 or more recent is required. You are using {sys.version}. "
        "Please use a newer version of Python."
    )
