"""Common base class for the ReadAlongs test suites"""

import tempfile
from pathlib import Path
from unittest import TestCase

from click.testing import CliRunner
from readalongs.log import LOGGER


class BasicTestCase(TestCase):
    """A Basic Unittest build block class that comes bundled with
    a temporary directory (self.tempdir), the path to the test data (self.data_dir)

    For convenience, self.tempdir and self.data_dir are pathlib.Path objects
    that can be used either with os.path functions or the shorter Path operators.
    E.g., these two lines are equivalent:
        text_file = os.path.join(self.data_dir, "ej-fra.txt")
        text_file = self.data_dir / "ej-fra.txt"
    """

    LOGGER.setLevel("DEBUG")
    data_dir = Path(__file__).parent / "data"

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
            self.tempdir = self.tempdirobj.name
        else:
            # Alternative tempdir code keeps it after running, for manual inspection:
            self.tempdir = tempfile.mkdtemp(prefix=tempdir_prefix, dir=".")
            print("tmpdir={}".format(self.tempdir))
        self.tempdir = Path(self.tempdir)

    def tearDown(self):
        """Clean up the temporary directory

        If a subclass needs its own tearDown() function, make sure to call
            super().tearDown()
        at the end of it.
        """
        if not self.keep_temp_dir_after_running:
            self.tempdirobj.cleanup()
