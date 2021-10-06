#!/usr/bin/env python3

import io
import os
import re
import sys
import tempfile
from shutil import copyfile
from unittest import TestCase, main

from basic_test_case import BasicTestCase

from readalongs.align import create_input_tei
from readalongs.app import app
from readalongs.cli import prepare
from readalongs.log import LOGGER


class TestPrepareCli(BasicTestCase):
    def setUp(self):
        super().setUp()
        self.empty_file = os.path.join(self.tempdir, "empty.txt")
        with io.open(self.empty_file, "wb"):
            pass

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

    def test_output_correct(self):
        input_file = os.path.join(self.data_dir, "fra.txt")
        xml_file = os.path.join(self.tempdir, "fra.xml")
        results = self.runner.invoke(prepare, ["-l", "fra", input_file, xml_file])
        self.assertEqual(results.exit_code, 0)

        ref_file = os.path.join(self.data_dir, "fra-prepared.xml")
        with open(xml_file) as output_f, open(ref_file) as ref_f:
            self.maxDiff = None
            self.assertListEqual(
                list(output_f),
                list(ref_f),
                f"output {xml_file} and reference {ref_file} differ.",
            )

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

    def test_prepare_with_different_newlines(self):
        sent = "Ceci est une phrase."
        linux_file = os.path.join(self.tempdir, "linux_file")
        with open(linux_file, mode="wb") as f:
            file_contents = sent + "\n\n" + sent + "\n\n\n" + sent + "\n"
            f.write(file_contents.encode("ascii"))
        linux_results = self.runner.invoke(prepare, ["-l", "fra", linux_file, "-"])
        linux_output = linux_results.output
        # The "Linux" output is the reference output, but we validate it a bit
        # too, with a regex: it has to have 2 pages and 3 paragraphs
        self.assertRegex(
            linux_output,
            re.compile(
                '<div type="page">.*<p>.*<p>.*<div type="page">.*<p>', re.DOTALL
            ),
        )

        no_eol_file = os.path.join(self.tempdir, "no_eol")
        with open(no_eol_file, mode="wb") as f:
            file_contents = sent + "\n\n" + sent + "\n\n\n" + sent
            f.write(file_contents.encode("ascii"))
        no_eol_results = self.runner.invoke(prepare, ["-l", "fra", no_eol_file, "-"])
        no_eol_output = no_eol_results.output
        self.assertEqual(
            linux_output,
            no_eol_output,
            "An absent final newline should not affect prepare",
        )

        dos_file = os.path.join(self.tempdir, "dos_file")
        with open(dos_file, mode="wb") as f:
            file_contents = sent + "\r\n\r\n" + sent + "\r\n\r\n\r\n" + sent + "\r\n"
            f.write(file_contents.encode("ascii"))
        dos_results = self.runner.invoke(prepare, ["-l", "fra", dos_file, "-"])
        dos_output = dos_results.output
        self.assertEqual(
            linux_output,
            dos_output,
            "Using DOS-style newlines should not affect prepare",
        )

        mac_file = os.path.join(self.tempdir, "mac_file")
        with open(mac_file, mode="wb") as f:
            file_contents = sent + "\r\r" + sent + "\r\r\r" + sent + "\r"
            f.write(file_contents.encode("ascii"))
        mac_results = self.runner.invoke(prepare, ["-l", "fra", mac_file, "-"])
        mac_output = mac_results.output
        self.assertEqual(
            linux_output,
            mac_output,
            "Using old Mac-style newlines should not affect prepare",
        )

    def test_create_input_tei_no_input(self):
        with self.assertRaises(RuntimeError):
            (fh, fname) = create_input_tei()


if __name__ == "__main__":
    main()
