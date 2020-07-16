from unittest import main, TestCase
import tempfile
import os
import io

from readalongs.log import LOGGER
from readalongs.app import app
from readalongs.cli import align


class TestAlignCli(TestCase):
    LOGGER.setLevel("DEBUG")
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    tempdirobj = tempfile.TemporaryDirectory(prefix="test_align_cli_tmpdir", dir=".")
    tempdir = tempdirobj.name

    def setUp(self):
        app.logger.setLevel("DEBUG")
        self.runner = app.test_cli_runner()

    def tearDown(self):
        pass

    def test_invoke_align(self):
        output = self.tempdir + "/output"
        # Run align from plain text
        results = self.runner.invoke(
            align,
            "-i -s -l fra {}/ej-fra.txt {}/ej-fra.m4a {}".format(
                self.data_dir, self.data_dir, output
            ),
        )
        self.assertTrue(
            os.path.exists(output + "/output.smil"),
            "successful alignment should have created output.smil",
        )

        # Move the alignment output to compare with further down
        # We cannot just output to a different name because changing the output file name
        # changes the contents of the output.
        os.rename(output, output + "1")
        self.assertFalse(os.path.exists(output), "os.rename should have moved dir")

        # Run align again, but on an XML input file with various added DNA text
        results_dna = self.runner.invoke(
            align,
            "-s {}/ej-fra-dna.xml {}/ej-fra.m4a {}".format(
                self.data_dir, self.data_dir, output
            ),
        )
        self.assertTrue(
            os.path.exists(output + "/output.smil"),
            "successful alignment with DNA should have created output.smil",
        )

        # Functionally the same as self.assertTrue(filecmp.cmp(f1, f2)), but show where
        # the differences are if the files are not identical
        self.assertListEqual(
            list(io.open(output + "1/output.smil")),
            list(io.open(output + "/output.smil")),
        )


if __name__ == "__main__":
    main()
