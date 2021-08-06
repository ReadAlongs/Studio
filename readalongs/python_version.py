"""
Specifies the minimum version of Python required for this project.
"""

import sys

# Please write this as a tuple of (major, minor, patch) verison:
MINIMUM_PYTHON_VERSION_REQUIRED = (3, 7, 0)


def ensure_using_supported_python_version():
    if sys.version_info < MINIMUM_PYTHON_VERSION_REQUIRED:
        raise Exception(
            "Python "
            + _version_to_str(MINIMUM_PYTHON_VERSION_REQUIRED)
            + " required (you are currently using Python "
            + _version_to_str(sys.version_info)
            + "). Please use a newer version of Python."
        )


def _version_to_str(version):
    major, minor, patch = version[:3]
    return "{major}.{minor}.{patch}".format(**locals())


ensure_using_supported_python_version()
