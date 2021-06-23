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

    # Set this to True to keep the temp dirs after running, for manual inspection
    # but please don't push a commit setting this to True!
    keep_temp_dir_after_running = True
    if not keep_temp_dir_after_running:
        tempdirobj = tempfile.TemporaryDirectory(
            prefix="tmpdir_test_align_cli_", dir="."
        )
        tempdir = tempdirobj.name
    else:
        tempdir = tempfile.mkdtemp(prefix="tmpdir_test_g2p_cli_", dir=".")
        print("tmpdir={}".format(tempdir))

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
                "--config",
                os.path.join(self.data_dir, "sample-config.json"),
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
        print(results.stdout)

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
                "--config",
                os.path.join(self.data_dir, "sample-config.json"),
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

        # We test error situations in the same test case, since we reuse the same outputs
        results_output_exists = self.runner.invoke(
            align,
            [
                os.path.join(self.data_dir, "ej-fra-dna.xml"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                output,
            ],
        )
        self.assertNotEqual(results_output_exists.exit_code, 0)
        self.assertIn(
            "already exists, use -f to overwrite", results_output_exists.output
        )

        # Output path exists as a regular file
        results_output_is_regular_file = self.runner.invoke(
            align,
            [
                os.path.join(self.data_dir, "ej-fra-dna.xml"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                os.path.join(output, "output.smil"),
            ],
        )
        self.assertNotEqual(results_output_is_regular_file, 0)
        self.assertIn(
            "already exists but is a not a directory",
            results_output_is_regular_file.output,
        )

    def test_permission_denied(self):
        dirname = os.path.join(self.tempdir, "permission_denied")
        os.mkdir(dirname, mode=0o444)
        results = self.runner.invoke(
            align,
            [
                "-f",
                os.path.join(self.data_dir, "ej-fra-dna.xml"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                dirname,
            ],
        )
        self.assertNotEqual(results, 0)
        self.assertIn("Cannot write into output folder", results.output)

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

    def test_invalid_config(self):
        # --config parameter needs to be <somefile>.json, text with .txt instead
        result = self.runner.invoke(
            align,
            [
                "--config",
                os.path.join(self.data_dir, "fra.txt"),
                os.path.join(self.data_dir, "fra.txt"),
                os.path.join(self.data_dir, "noise.mp3"),
                os.path.join(self.tempdir, "out-invalid-config-1"),
            ],
        )
        self.assertIn("must be in JSON format", result.stdout)

        # --config parameters needs to contain valid json, test with garbage
        config_file = os.path.join(self.tempdir, "bad-config.json")
        with open(config_file, "w") as f:
            print("not valid json", file=f)
        result = self.runner.invoke(
            align,
            [
                "--config",
                config_file,
                os.path.join(self.data_dir, "fra.txt"),
                os.path.join(self.data_dir, "noise.mp3"),
                os.path.join(self.tempdir, "out-invalid-config-2"),
            ],
        )
        self.assertIn("is not in valid JSON format", result.stdout)


if __name__ == "__main__":
    main()
