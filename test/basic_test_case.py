import os
import tempfile
from unittest import TestCase, main

from readalongs.app import app
from readalongs.log import LOGGER


class BasicTestCase(TestCase):
    """A Basic Unittest build block class that comes bundled with
    a temporary directory (tempdir), and access to an app runner
    (self.runner)
    """

    LOGGER.setLevel("DEBUG")
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    # Set this to True to keep the temp dirs after running, for manual inspection
    # but please don't push a commit setting this to True!
    keep_temp_dir_after_running = False

    def setUp(self):
        app.logger.setLevel("DEBUG")
        self.runner = app.test_cli_runner()
        tempdir_prefix = f"tmpdir_{type(self).__name__}_"
        if not self.keep_temp_dir_after_running:
            self.tempdirobj = tempfile.TemporaryDirectory(
                prefix=tempdir_prefix, dir="."
            )
            self.tempdir = self.tempdirobj.name
        else:
            # Alternative tempdir code keeps it after running, for manual inspection:
            self.tempdir = tempfile.mkdtemp(prefix=tempdir_prefix, dir=".")
            print("tmpdir={}".format(self.tempdir))

    def tearDown(self):
        if not self.keep_temp_dir_after_running:
            self.tempdirobj.cleanup()
