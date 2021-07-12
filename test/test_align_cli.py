#!/usr/bin/env python3

import io
import os
import tempfile
from os.path import exists, join
from unittest import TestCase, main

from readalongs.app import app
from readalongs.cli import align
from readalongs.log import LOGGER


class TestAlignCli(TestCase):
    LOGGER.setLevel("DEBUG")
    data_dir = join(os.path.dirname(__file__), "data")

    # Set this to True to keep the temp dirs after running, for manual inspection
    # but please don't push a commit setting this to True!
    keep_temp_dir_after_running = False
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
        output = join(self.tempdir, "output")
        with open("image-for-page1.jpg", "w"):
            pass
        # Run align from plain text
        results = self.runner.invoke(
            align,
            [
                "-i",
                "-s",
                "-l",
                "fra",
                "--config",
                join(self.data_dir, "sample-config.json"),
                join(self.data_dir, "ej-fra.txt"),
                join(self.data_dir, "ej-fra.m4a"),
                output,
            ],
        )
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(
            exists(join(output, "output.smil")),
            "successful alignment should have created output.smil",
        )
        self.assertTrue(
            exists(join(output, "index.html")),
            "successful alignment should have created index.html",
        )
        with open(join(output, "index.html")) as f:
            self.assertIn(
                '<read-along text="output.xml" alignment="output.smil" audio="output.m4a"',
                f.read(),
            )
        self.assertTrue(
            exists(join(output, "tempfiles", "output.tokenized.xml")),
            "alignment with -s should have created tempfiles/output.tokenized.xml",
        )
        self.assertTrue(
            exists(join(output, "assets", "image-for-page1.jpg")),
            "alignment with image files should have copied image-for-page1.jpg to assets",
        )
        self.assertIn("image-for-page2.jpg is accessible ", results.stdout)
        os.unlink("image-for-page1.jpg")
        self.assertFalse(exists("image-for-page1.jpg"))
        # print(results.stdout)

        # Move the alignment output to compare with further down
        # We cannot just output to a different name because changing the output file name
        # changes the contents of the output.
        output1 = output + "1"
        os.rename(output, output1)
        self.assertFalse(exists(output), "os.rename() should have moved dir")

        # Run align again, but on an XML input file with various added DNA text
        results_dna = self.runner.invoke(
            align,
            [
                "-s",
                "--config",
                join(self.data_dir, "sample-config.json"),
                join(self.data_dir, "ej-fra-dna.xml"),
                join(self.data_dir, "ej-fra.m4a"),
                output,
            ],
        )
        self.assertEqual(results_dna.exit_code, 0)
        # print(results_dna.stdout)
        self.assertTrue(
            exists(join(output, "output.smil")),
            "successful alignment with DNA should have created output.smil",
        )
        self.assertIn("Please copy image-for-page1.jpg to ", results_dna.stdout)
        self.assertFalse(
            exists(join(output, "assets", "image-for-page1.jpg")),
            "image-for-page1.jpg was not on disk, cannot have been copied",
        )

        # Functionally the same as self.assertTrue(filecmp.cmp(f1, f2)), but show where
        # the differences are if the files are not identical
        with open(join(output1, "output.smil")) as f1, open(
            join(output, "output.smil")
        ) as f2:
            self.assertListEqual(list(f1), list(f2))

        # We test error situations in the same test case, since we reuse the same outputs
        results_output_exists = self.runner.invoke(
            align,
            [
                join(self.data_dir, "ej-fra-dna.xml"),
                join(self.data_dir, "ej-fra.m4a"),
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
                join(self.data_dir, "ej-fra-dna.xml"),
                join(self.data_dir, "ej-fra.m4a"),
                join(output, "output.smil"),
            ],
        )
        self.assertNotEqual(results_output_is_regular_file, 0)
        self.assertIn(
            "already exists but is a not a directory",
            results_output_is_regular_file.output,
        )

    def test_permission_denied(self):
        dir = join(self.tempdir, "permission_denied")
        os.mkdir(dir, mode=0o444)
        results = self.runner.invoke(
            align,
            [
                "-f",
                join(self.data_dir, "ej-fra-dna.xml"),
                join(self.data_dir, "ej-fra.m4a"),
                dir,
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
        input_filename = join(self.tempdir, "input")
        with open(input_filename, "w") as f:
            f.write(input)
        output_dir = join(self.tempdir, "eng-output")
        # Run align from plain text
        self.runner.invoke(
            align,
            [
                "-i",
                "-s",
                "-l",
                "eng",
                input_filename,
                join(self.data_dir, "ej-fra.m4a"),
                output_dir,
            ],
        )

        g2p_ref = '<s id="t0b0d0p0s0"><w id="t0b0d0p0s0w0" ARPABET="DH IH S">This</w> <w id="t0b0d0p0s0w1" ARPABET="IH Z">is</w> <w id="t0b0d0p0s0w2" ARPABET="S AH M">some</w> <w id="t0b0d0p0s0w3" ARPABET="T EH K S T">text</w> <w id="t0b0d0p0s0w4" ARPABET="DH AE T">that</w> <w id="t0b0d0p0s0w5" ARPABET="W IY">we</w> <w id="t0b0d0p0s0w6" ARPABET="W IH L">will</w> <w id="t0b0d0p0s0w7" ARPABET="R AH N">run</w> <w id="t0b0d0p0s0w8" ARPABET="TH R UW">through</w> <w id="t0b0d0p0s0w9" ARPABET="DH AH">the</w> <w id="t0b0d0p0s0w10" ARPABET="IH NG G L IH SH">English</w> <w id="t0b0d0p0s0w11" ARPABET="L EH K S IH K AA N">lexicon</w> <w id="t0b0d0p0s0w12" ARPABET="G R AE F IY M">grapheme</w> <w id="t0b0d0p0s0w13" ARPABET="T UW">to</w> <w id="t0b0d0p0s0w14" ARPABET="M AO R F IY M">morpheme</w> <w id="t0b0d0p0s0w15" ARPABET="AH P R OW CH">approach</w>.</s>'

        tokenized_file = join(
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
                join(self.data_dir, "fra.txt"),
                join(self.data_dir, "fra.txt"),
                join(self.data_dir, "noise.mp3"),
                join(self.tempdir, "out-invalid-config-1"),
            ],
        )
        self.assertIn("must be in JSON format", result.stdout)

        # --config parameters needs to contain valid json, test with garbage
        config_file = join(self.tempdir, "bad-config.json")
        with open(config_file, "w") as f:
            print("not valid json", file=f)
        result = self.runner.invoke(
            align,
            [
                "--config",
                config_file,
                join(self.data_dir, "fra.txt"),
                join(self.data_dir, "noise.mp3"),
                join(self.tempdir, "out-invalid-config-2"),
            ],
        )
        self.assertIn("is not in valid JSON format", result.stdout)


if __name__ == "__main__":
    main()
