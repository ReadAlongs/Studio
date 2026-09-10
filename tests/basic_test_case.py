"""Common base class for the ReadAlongs test suites"""

import logging
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

import readalongs.text.make_package as make_package
from readalongs.log import LOGGER

make_package.FETCH_BUNDLE_TIMEOUT_SECONDS = 5  # shorter timeout for testing


class BasicTestCase:
    """A pytest building block class that comes bundled with
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

    @pytest.fixture(autouse=True)
    def _pytest_setup(self):
        """Create per-test temporary state and run an optional subclass hook."""
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
            print(f"tmpdir={tempdir_name}")
        self.tempdir = Path(tempdir_name)

        setup = getattr(self, "_setUp", None)
        if setup is not None:
            setup()

        yield

        if not self.keep_temp_dir_after_running:
            self.tempdirobj.cleanup()

        if LOGGER.level == logging.DEBUG:
            # LOGGER.error("Logging level is DEBUG")
            # Some test cases can set the logging level to DEBUG when they pass
            # --debug to a CLI command, but don't let that affect subsequent tests.
            LOGGER.setLevel(logging.INFO)
