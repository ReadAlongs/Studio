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
        output = os.path.join(self.tempdir, "output")
        # Run align from plain text
        results = self.runner.invoke(
            align,
            [
                "-i",
                "-s",
                "-l",
                "fra",
                os.path.join(self.data_dir, "ej-fra.txt"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                output,
            ],
        )
        self.assertTrue(
            os.path.exists(os.path.join(output, "output.smil")),
            "successful alignment should have created output.smil",
        )

        # Move the alignment output to compare with further down
        # We cannot just output to a different name because changing the output file name
        # changes the contents of the output.
        output1 = output + "1"
        os.rename(output, output1)
        self.assertFalse(os.path.exists(output), "os.rename() should have moved dir")

        # Run align again, but on an XML input file with various added DNA text
        results_dna = self.runner.invoke(
            align,
            [
                "-s",
                os.path.join(self.data_dir, "ej-fra-dna.xml"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                output,
            ],
        )
        self.assertTrue(
            os.path.exists(os.path.join(output, "output.smil")),
            "successful alignment with DNA should have created output.smil",
        )

        # Functionally the same as self.assertTrue(filecmp.cmp(f1, f2)), but show where
        # the differences are if the files are not identical
        with open(os.path.join(output1, "output.smil")) as f1, open(
            os.path.join(output, "output.smil")
        ) as f2:
            self.assertListEqual(list(f1), list(f2))


if __name__ == "__main__":
    main()
