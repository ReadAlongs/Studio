"""Common base class for the ReadAlongs test suites"""

import logging
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import TestCase

from click.testing import CliRunner

import readalongs.text.make_package as make_package
from readalongs.log import LOGGER

make_package.FETCH_BUNDLE_TIMEOUT_SECONDS = 5  # shorter timeout for testing


class BasicTestCase(TestCase):
    """A Basic Unittest build block class that comes bundled with
    a temporary directory (self.tempdir), the path to the test data (self.data_dir)

    For convenience, self.tempdir and self.data_dir are pathlib.Path objects
    that can be used either with os.path functions or the shorter Path operators.
    E.g., these two lines are equivalent:
        text_file = os.path.join(self.data_dir, "ej-fra.txt")
        text_file = self.data_dir / "ej-fra.txt"
    """

    data_dir = Path(__file__).parent / "data"
    tempdir: Path

    # Set this to True to keep the temp dirs after running, for manual inspection
    # but please don't push a commit setting this to True!
    # To keep temp dirs for just one subclass, add this line to its setUp() function:
    # function before the call to super().setUp():
    #     self.keep_temp_dir_after_running = True
    keep_temp_dir_after_running = False

    def setUp(self):
        """Create a temporary directory, self.tempdir, and a test runner, self.runner

        If a subclass needs its own setUp() function, make sure to call
            super().setUp()
        at the beginning of it.
        """
        self.runner = CliRunner()
        tempdir_prefix = f"tmpdir_{type(self).__name__}_"
        if not self.keep_temp_dir_after_running:
            self.tempdirobj = tempfile.TemporaryDirectory(
                prefix=tempdir_prefix, dir="."
            )
            tempdir_name = self.tempdirobj.name
        else:
            # Alternative tempdir code keeps it after running, for manual inspection:
            tempdir_name = tempfile.mkdtemp(prefix=tempdir_prefix, dir=".")
            print("tmpdir={}".format(tempdir_name))
        self.tempdir = Path(tempdir_name)

    def tearDown(self):
        """Clean up the temporary directory

        If a subclass needs its own tearDown() function, make sure to call
            super().tearDown()
        at the end of it.
        """
        if not self.keep_temp_dir_after_running:
            self.tempdirobj.cleanup()

        if LOGGER.level == logging.DEBUG:
            # LOGGER.error("Logging level is DEBUG")
            # Some test cases can set the logging level to DEBUG when they pass
            # --debug to a CLI command, but don't let that affect subsequent tests.
            LOGGER.setLevel(logging.INFO)


@contextmanager
def silence_c_stderr():
    """Capture stderr from C output, e.g., from SoundSwallower.

    Note: to capture stderr for both C and Python code, combine this with
    redirect_stderr(), but you must use capture_c_stderr() first:
        with capture_c_stderr(), redirect_stderr(io.StringIO()):
            # code

    Loosely inspired by https://stackoverflow.com/a/24277852, but much simplified to
    address our narrow needs, namely to silence stderr in a context manager.
    """

    if os.name == "nt" and sys.version_info < (3, 10):
        yield  # work around instability for this on Windows with Py 3.8/3.9
    else:
        stderr_fileno = sys.stderr.fileno()
        stderr_save = os.dup(stderr_fileno)
        stderr_fd = os.open(os.devnull, os.O_RDWR)
        os.dup2(stderr_fd, stderr_fileno)
        yield
        os.dup2(stderr_save, stderr_fileno)
        os.close(stderr_save)
        os.close(stderr_fd)


@contextmanager
def silence_logs():
    LOGGER.disabled = True
    yield
    LOGGER.disabled = False
