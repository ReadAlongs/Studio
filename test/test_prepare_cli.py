#!/usr/bin/env python3

import io
import os
import sys
import tempfile
from shutil import copyfile
from unittest import TestCase, main

from readalongs.app import app
from readalongs.cli import prepare
from readalongs.log import LOGGER


class TestPrepareCli(TestCase):
    LOGGER.setLevel("DEBUG")
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    def setUp(self):
        app.logger.setLevel("DEBUG")
        self.runner = app.test_cli_runner()
        self.tempdirobj = tempfile.TemporaryDirectory(
            prefix="test_prepare_cli_tmpdir", dir="."
        )
        self.tempdir = self.tempdirobj.name
        # Alternative tempdir code keeps it after running, for manual inspection:
        # self.tempdir = tempfile.mkdtemp(prefix="test_prepare_cli_tmpdir", dir=".")
        # print('tmpdir={}'.format(self.tempdir))
        self.empty_file = os.path.join(self.tempdir, "empty.txt")
        with io.open(self.empty_file, "wb") as f:
            pass

    def tearDown(self):
        self.tempdirobj.cleanup()

    def test_invoke_prepare(self):
        results = self.runner.invoke(
            prepare,
            ["-l", "atj", "-d", self.empty_file, os.path.join(self.tempdir, "delme")],
        )
        self.assertEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "Running readalongs prepare")
        # print('Prepare.stdout: {}'.format(results.stdout))

    def test_no_lang(self):
        results = self.runner.invoke(
            prepare, [self.empty_file, self.empty_file + ".xml"]
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "Missing.*language")

    def test_inputfile_not_exist(self):
        results = self.runner.invoke(prepare, "-l atj /file/does/not/exist delme")
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "No such file or directory")

    def test_outputfile_exists(self):
        results = self.runner.invoke(
            prepare,
            ["-l", "atj", self.empty_file, os.path.join(self.tempdir, "exists")],
        )
        results = self.runner.invoke(
            prepare,
            ["-l", "atj", self.empty_file, os.path.join(self.tempdir, "exists")],
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "exists.*overwrite")

    def test_output_exists(self):
        xmlfile = os.path.join(self.tempdir, "fra.xml")
        results = self.runner.invoke(
            prepare, ["-l", "fra", os.path.join(self.data_dir, "fra.txt"), xmlfile]
        )
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(xmlfile), "output xmlfile did not get created")

    def test_input_is_stdin(self):
        results = self.runner.invoke(prepare, "-l fra -", input="Ceci est un test.")
        # LOGGER.warning("Output: {}".format(results.output))
        # LOGGER.warning("Exception: {}".format(results.exception))
        self.assertEqual(results.exit_code, 0)
        self.assertIn("<s>Ceci est un test", results.stdout)
        self.assertIn('<text xml:lang="fra">', results.stdout)

    def test_generate_output_name(self):
        input_file = os.path.join(self.tempdir, "someinput.txt")
        copyfile(os.path.join(self.data_dir, "fra.txt"), input_file)
        results = self.runner.invoke(prepare, ["-l", "fra", input_file])
        LOGGER.warning("Output: {}".format(results.output))
        LOGGER.warning("Exception: {}".format(results.exception))
        self.assertEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "Wrote.*someinput[.]xml")
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, "someinput.xml")))


if __name__ == "__main__":
    main()
