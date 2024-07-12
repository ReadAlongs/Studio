#!/usr/bin/env python

"""Test suite for the readalongs make_xml CLI command"""

import io
import os
import re
from shutil import copyfile
from unittest import main

from basic_test_case import BasicTestCase

# from readalongs.log import LOGGER
from readalongs._version import READALONG_FILE_FORMAT_VERSION, VERSION
from readalongs.align import create_input_ras, create_ras_from_text
from readalongs.cli import align, make_xml


def updateFormatVersion(input):
    return input.replace("{{format_version}}", READALONG_FILE_FORMAT_VERSION)


def updateStudioVersion(input):
    return input.replace("{{studio_version}}", VERSION)


class TestMakeXMLCli(BasicTestCase):
    """Test suite for the readalongs make-xml CLI command"""

    def setUp(self):
        super().setUp()
        self.empty_file = os.path.join(self.tempdir, "empty.txt")
        with io.open(self.empty_file, "wb"):
            pass

    def test_invoke_prepare(self):
        """Basic usage of deprecated readalongs prepare"""
        results = self.runner.invoke(
            make_xml,
            ["-l", "atj", "-d", self.empty_file, os.path.join(self.tempdir, "delme")],
        )
        self.assertEqual(results.exit_code, 0)

    def test_invoke_make_xml(self):
        """Basic usage of readalongs make-xml"""
        results = self.runner.invoke(
            make_xml,
            ["-l", "atj", "-d", self.empty_file, os.path.join(self.tempdir, "delme")],
        )
        self.assertEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "Running readalongs make-xml")

    def test_no_lang(self):
        """Error case: readalongs make-xml without the mandatory -l switch"""
        results = self.runner.invoke(
            make_xml, [self.empty_file, self.empty_file + ".readalong"]
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "Missing.*language")

    def test_inputfile_not_exist(self):
        """Error case: input file does not exist"""
        results = self.runner.invoke(make_xml, "-l atj /file/does/not/exist delme")
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "No such file or directory")

    def test_outputfile_exists(self):
        """Existing output file should not be overwritten by readalongs make-xml by default"""
        results = self.runner.invoke(
            make_xml,
            ["-l", "atj", self.empty_file, os.path.join(self.tempdir, "exists")],
        )
        results = self.runner.invoke(
            make_xml,
            ["-l", "atj", self.empty_file, os.path.join(self.tempdir, "exists")],
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "exists.*overwrite")

    def test_output_exists(self):
        """Make sure readalongs make-xml create the expected output file"""
        xmlfile = os.path.join(self.tempdir, "fra.readalong")
        results = self.runner.invoke(
            make_xml, ["-l", "fra", os.path.join(self.data_dir, "fra.txt"), xmlfile]
        )
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(xmlfile), "output xmlfile did not get created")

    def test_output_correct(self):
        """Make sure the contents of readalongs make-xml's output file is correct."""
        input_file = os.path.join(self.data_dir, "fra.txt")
        xml_file = os.path.join(self.tempdir, "fra.readalong")
        results = self.runner.invoke(make_xml, ["-l", "fra", input_file, xml_file])
        self.assertEqual(results.exit_code, 0)

        ref_file = os.path.join(self.data_dir, "fra-prepared.readalong")
        with open(xml_file, encoding="utf8") as output_f, open(
            ref_file, encoding="utf8"
        ) as ref_f:
            self.maxDiff = None
            # update version info
            ref_list = list(ref_f)
            ref_list[1] = updateFormatVersion(ref_list[1])
            ref_list[2] = updateStudioVersion(ref_list[2])
            self.assertListEqual(
                list(output_f),
                ref_list,
                f"output {xml_file} and reference {ref_file} differ.",
            )

    def test_input_is_stdin(self):
        """Validate that readalongs make-xml can use stdin as input"""
        results = self.runner.invoke(make_xml, "-l fra -", input="Ceci est un test.")
        # LOGGER.warning("Output: {}".format(results.output))
        # LOGGER.warning("Exception: {}".format(results.exception))
        self.assertEqual(results.exit_code, 0)
        self.assertIn("<s>Ceci est un test", results.stdout)
        self.assertIn('<text xml:lang="fra"', results.stdout)

    def test_generate_output_name(self):
        """Validate readalongs make-xml generating the output file name"""
        input_file = os.path.join(self.tempdir, "someinput.txt")
        copyfile(os.path.join(self.data_dir, "fra.txt"), input_file)
        results = self.runner.invoke(make_xml, ["-l", "fra", input_file])
        # LOGGER.warning("Output: {}".format(results.output))
        # LOGGER.warning("Exception: {}".format(results.exception))
        self.assertEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "Wrote.*someinput[.]readalong")
        self.assertTrue(
            os.path.exists(os.path.join(self.tempdir, "someinput.readalong"))
        )

    def test_make_xml_with_different_newlines(self):
        """readalongs make-xml handling single and double blank lines for paragraphs and pages"""
        sent = "Ceci est une phrase."
        linux_file = os.path.join(self.tempdir, "linux_file")
        with open(linux_file, mode="wb") as f:
            file_contents = sent + "\n\n" + sent + "\n\n\n" + sent + "\n"
            f.write(file_contents.encode("ascii"))
        linux_results = self.runner.invoke(make_xml, ["-l", "fra", linux_file, "-"])
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
        no_eol_results = self.runner.invoke(make_xml, ["-l", "fra", no_eol_file, "-"])
        no_eol_output = no_eol_results.output
        self.assertEqual(
            linux_output,
            no_eol_output,
            "An absent final newline should not affect make-xml",
        )

        dos_file = os.path.join(self.tempdir, "dos_file")
        with open(dos_file, mode="wb") as f:
            file_contents = sent + "\r\n\r\n" + sent + "\r\n\r\n\r\n" + sent + "\r\n"
            f.write(file_contents.encode("ascii"))
        dos_results = self.runner.invoke(make_xml, ["-l", "fra", dos_file, "-"])
        dos_output = dos_results.output
        self.assertEqual(
            linux_output,
            dos_output,
            "Using DOS-style newlines should not affect make-xml",
        )

        mac_file = os.path.join(self.tempdir, "mac_file")
        with open(mac_file, mode="wb") as f:
            file_contents = sent + "\r\r" + sent + "\r\r\r" + sent + "\r"
            f.write(file_contents.encode("ascii"))
        mac_results = self.runner.invoke(make_xml, ["-l", "fra", mac_file, "-"])
        mac_output = mac_results.output
        self.assertEqual(
            linux_output,
            mac_output,
            "Using old Mac-style newlines should not affect make-xml",
        )

    def test_create_input_ras_errors(self):
        """create_input_ras should raise a AssertionError when parameters are missing."""
        # These used to be RuntimeError, but that was not right: *programmer*
        # errors can and should dump stack traces, unlike *user* errors, which
        # warrant nice friendly messages.
        with self.assertRaises(AssertionError):
            # missing input_file_name or input_file_handle
            _, _ = create_input_ras()

        with self.assertRaises(AssertionError):
            # missing text_languages
            _, _ = create_input_ras(
                input_file_name=os.path.join(self.data_dir, "fra.txt")
            )

    def test_make_xml_multiple_langs(self):
        """Giving multiple langs to -l replaces the old --g2p-fallback option."""
        input_file = os.path.join(self.data_dir, "fra.txt")
        results = self.runner.invoke(
            make_xml, ["-l", "fra", "-l", "iku:und", input_file, "-"]
        )
        self.assertEqual(results.exit_code, 0)
        self.assertIn('<text xml:lang="fra" fallback-langs="iku,und">', results.output)
        results = self.runner.invoke(make_xml, ["-l", "fra,iku:und", input_file, "-"])
        self.assertEqual(results.exit_code, 0)
        self.assertIn('<text xml:lang="fra" fallback-langs="iku,und">', results.output)
        results = self.runner.invoke(
            make_xml, ["-l", "fra:iku", "-l", "und", input_file, "-"]
        )
        self.assertEqual(results.exit_code, 0)
        self.assertIn('<text xml:lang="fra" fallback-langs="iku,und">', results.output)

    def test_make_xml_invalid_lang(self):
        input_file = os.path.join(self.data_dir, "fra.txt")
        results = self.runner.invoke(
            make_xml, ["-l", "fra:notalang:und", input_file, "-"]
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.output, r"Invalid value.*'notalang'")

    def test_make_xml_invalid_utf8_input(self):
        noise_file = os.path.join(self.data_dir, "noise.mp3")

        # Read noise.mp3 as if it was utf8 text, via create_input_ras(input_file_handle)
        results = self.runner.invoke(make_xml, ["-l", "fra", noise_file, "-"])
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("provide a correctly encoded utf-8", results.output)

        # Read noise.mp3 as if it was utf8 text, via create_input_ras(input_file_name)
        results = self.runner.invoke(
            make_xml,
            ["-l", "fra", noise_file, os.path.join(self.tempdir, "noise.readalong")],
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("provide a correctly encoded utf-8", results.output)

        # align also calls create_input_ras(input_file_name)
        results = self.runner.invoke(
            align,
            [
                "-l",
                "fra",
                noise_file,
                noise_file,
                os.path.join(self.tempdir, "noise-out"),
            ],
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("provide a correctly encoded utf-8", results.output)

    def test_blank_lines_stripped(self):
        """Blank lines for paragraph and page breaks are allowed to have whitespace"""
        input_text_with_spaces = "Ceci est un test\n \nParagraphe\n\t \n \nPage\n"
        input_text_stripped = "Ceci est un test\n\nParagraphe\n\n\nPage\n"

        self.assertEqual(
            create_ras_from_text(text2lines(input_text_with_spaces), ["fra"]),
            create_ras_from_text(text2lines(input_text_stripped), ["fra"]),
        )

    def test_ignore_superfluous_blank_lines(self):
        """Don't insert blank pages when there are more blank lines than required."""
        input_text_with_extra_nls = (
            " \nPage1\n \n  \n\nPage2\n\t\n \n\n\t\n\n\nPage3\n\n\t\n\t"
        )
        input_text_stripped = "Page1\n\n\nPage2\n\n\nPage3"

        self.maxDiff = None
        self.assertEqual(
            create_ras_from_text(text2lines(input_text_with_extra_nls), ["eng"]),
            create_ras_from_text(text2lines(input_text_stripped), ["eng"]),
        )

        for n in range(3, 10):
            self.assertEqual(
                create_ras_from_text(text2lines("Page1" + "\n" * n + "Page2"), ["eng"]),
                create_ras_from_text(text2lines("Page1" + "\n" * 3 + "Page2"), ["eng"]),
            )

    def test_split_vs_readlines(self):
        """Calling create_ras_from_text should work any way we split the lines"""
        # string.split("\n") strips newlines and might not be identical to readlines(),
        # but that should make no difference to create_tei_from_text
        text = "Blah\nBlah\n\nFoo \n\n \nBar"
        self.assertEqual(
            create_ras_from_text(text.split("\n"), ["eng"]),
            create_ras_from_text(text2lines(text), ["eng"]),
        )


def text2lines(text: str):
    """Stub: readlines() from a string as if it was a file"""
    return io.StringIO(text).readlines()


if __name__ == "__main__":
    main()
