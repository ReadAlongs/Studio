#!/usr/bin/env python3

import io
import os
import tempfile
from unittest import TestCase, main

from readalongs.app import app
from readalongs.cli import align
from readalongs.log import LOGGER


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
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(
            os.path.exists(os.path.join(output, "output.smil")),
            "successful alignment should have created output.smil",
        )
        self.assertTrue(
            os.path.exists(os.path.join(output, "index.html")),
            "successful alignment should have created index.html",
        )
        with open(os.path.join(output, "index.html")) as f:
            self.assertIn(
                '<read-along text="output.xml" alignment="output.smil" audio="output.m4a"',
                f.read(),
            )
        self.assertTrue(
            os.path.exists(os.path.join(output, "tempfiles", "output.tokenized.xml")),
            "alignment with -s should have created tempfiles/output.tokenized.xml",
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
        self.assertEqual(results_dna.exit_code, 0)
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

    def test_align_help(self):
        # Validates that readalongs align -h lists all in-langs that can map to eng-arpabet
        results = self.runner.invoke(align, "-h")
        self.assertEqual(results.exit_code, 0)
        self.assertIn("|crg-tmd|", results.stdout)
        self.assertIn("|crg-dv|", results.stdout)
        self.assertNotIn("|crg|", results.stdout)

    def test_align_english(self):
        # Validates that LexiconG2P words for English language alignment
        input = "This is some text that we will run through the English lexicon grapheme to morpheme approach."
        input_filename = os.path.join(self.tempdir, "input")
        with open(input_filename, "w") as f:
            f.write(input)
        output_dir = os.path.join(self.tempdir, "eng-output")
        # Run align from plain text
        self.runner.invoke(
            align,
            [
                "-i",
                "-s",
                "-l",
                "eng",
                input_filename,
                os.path.join(self.data_dir, "ej-fra.m4a"),
                output_dir,
            ],
        )

        g2p_ref = '<s id="t0b0d0p0s0"><w id="t0b0d0p0s0w0">DH IH S</w> <w id="t0b0d0p0s0w1">IH Z</w> <w id="t0b0d0p0s0w2">S AH M</w> <w id="t0b0d0p0s0w3">T EH K S T</w> <w id="t0b0d0p0s0w4">DH AE T</w> <w id="t0b0d0p0s0w5">W IY</w> <w id="t0b0d0p0s0w6">W IH L</w> <w id="t0b0d0p0s0w7">R AH N</w> <w id="t0b0d0p0s0w8">TH R UW</w> <w id="t0b0d0p0s0w9">DH AH</w> <w id="t0b0d0p0s0w10">IH NG G L IH SH</w> <w id="t0b0d0p0s0w11">L EH K S IH K AA N</w> <w id="t0b0d0p0s0w12">G R AE F IY M</w> <w id="t0b0d0p0s0w13">T UW</w> <w id="t0b0d0p0s0w14">M AO R F IY M</w> <w id="t0b0d0p0s0w15">AH P R OW CH</w>.</s>'

        tokenized_file = os.path.join(
            self.tempdir, "eng-output", "tempfiles", "eng-output.g2p.xml"
        )
        with open(tokenized_file, "r") as f:
            tok_output = f.read()

        self.assertIn(g2p_ref, tok_output)


if __name__ == "__main__":
    main()
