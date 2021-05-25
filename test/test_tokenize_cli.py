#!/usr/bin/env python3

import io
import os
import sys
import tempfile
from shutil import copyfile
from unittest import TestCase, main

from readalongs.app import app
from readalongs.cli import prepare, tokenize
from readalongs.log import LOGGER


class TestTokenizeCli(TestCase):
    LOGGER.setLevel("DEBUG")
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    # Set this to True to keep the temp dirs after running, for manual inspection
    # but please don't push a commit setting this to True!
    keep_temp_dir_after_running = False

    def setUp(self):
        app.logger.setLevel("DEBUG")
        self.runner = app.test_cli_runner()
        if not self.keep_temp_dir_after_running:
            self.tempdirobj = tempfile.TemporaryDirectory(
                prefix="tmpdir_test_tokenize_cli_", dir="."
            )
            self.tempdir = self.tempdirobj.name
        else:
            # Alternative tempdir code keeps it after running, for manual inspection:
            self.tempdir = tempfile.mkdtemp(prefix="tmpdir_test_tokenize_cli_", dir=".")
            print("tmpdir={}".format(self.tempdir))

        self.xmlfile = os.path.join(self.tempdir, "fra.xml")
        _ = self.runner.invoke(
            prepare, ["-l", "fra", os.path.join(self.data_dir, "fra.txt"), self.xmlfile]
        )

    def tearDown(self):
        if not self.keep_temp_dir_after_running:
            self.tempdirobj.cleanup()

    def test_invoke_tok(self):
        results = self.runner.invoke(
            tokenize, [self.xmlfile, os.path.join(self.tempdir, "delme")]
        )
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, "delme.xml")))

    def test_generate_output_name(self):
        results = self.runner.invoke(tokenize, ["--debug", self.xmlfile])
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, "fra.tokenized.xml")))

    def test_with_stdin(self):
        with io.open(self.xmlfile) as f:
            inputtext = f.read()
        results = self.runner.invoke(tokenize, "-", input=inputtext)
        self.assertEqual(results.exit_code, 0)
        self.assertIn(
            "<s><w>Ceci</w> <w>est</w> <w>une</w> <w>phrase</w>", results.output
        )

    def test_file_already_exists(self):
        results = self.runner.invoke(tokenize, [self.xmlfile, self.xmlfile])
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("use -f to overwrite", results.output)

    def test_bad_input(self):
        results = self.runner.invoke(tokenize, "- -", input="this is not XML!")
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Error parsing", results.output)
        # LOGGER.warning("Output: {}".format(results.output))
        # LOGGER.warning("Exception: {}".format(results.exception))

    def test_lang_id(self):
        xml_file = os.path.join(self.tempdir, "no_lang_id.xml")
        with open(xml_file, "w") as f:
            print(
                "<?xml version='1.0' encoding='utf-8'?><TEI><text><body><div type=\"page\"><p>\n"
                "<s>this is a test</s>\n"
                "<s>en français été évident?</s>\n"
                "<s>ᓄᓇᕗᑦ</s>\n"
                "</p></div></body></text></TEI>",
                file=f,
            )
        results = self.runner.invoke(tokenize, [xml_file, "-"])
        self.assertEqual(results.exit_code, 0)
        self.assertIn("s xml:lang=", results.output)


if __name__ == "__main__":
    main()
