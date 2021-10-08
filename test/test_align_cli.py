#!/usr/bin/env python3

import io
import os
import re
import tempfile
from os.path import exists, join
from unittest import TestCase, main

from basic_test_case import BasicTestCase
from lxml.html import fromstring

from readalongs.app import app
from readalongs.cli import align
from readalongs.log import LOGGER


class TestAlignCli(BasicTestCase):
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
                "-C",
                "-t",
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
        expected_output_files = [
            "output.smil",
            "output.xml",
            "output.m4a",
            "index.html",
            "output.TextGrid",
            "output.eaf",
            "output_sentences.srt",
            "output_sentences.vtt",
            "output_words.srt",
            "output_words.vtt",
        ]
        for f in expected_output_files:
            self.assertTrue(
                exists(join(output, f)), f"successful alignment should have created {f}"
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
                "-x",
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
        self.assertTrue(
            exists(join(output, "output.xhtml")),
            "successful alignment with -x should have created output.xhtml",
        )
        self.assertIn("Please copy image-for-page1.jpg to ", results_dna.stdout)
        self.assertFalse(
            exists(join(output, "assets", "image-for-page1.jpg")),
            "image-for-page1.jpg was not on disk, cannot have been copied",
        )

        # Functionally the same as self.assertTrue(filecmp.cmp(f1, f2)), but show where
        # the differences are if the files are not identical
        # Since f2 was created using -x, we need to substitute .xhtml back to .xml during
        # the comparison of the contents of the .smil files.
        with open(join(output1, "output.smil")) as f1, open(
            join(output, "output.smil")
        ) as f2:
            self.assertListEqual(
                list(f1), [line.replace(".xhtml", ".xml") for line in f2]
            )

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

    def test_align_with_package(self):
        """Test creating a single-file package, with --html"""

        output = join(self.tempdir, "html")
        results_html = self.runner.invoke(
            align,
            [
                join(self.data_dir, "ej-fra-package.xml"),
                join(self.data_dir, "ej-fra.m4a"),
                output,
                "--html",
            ],
        )
        self.assertEqual(results_html.exit_code, 0)
        self.assertTrue(
            exists(join(output, "html.html")),
            "succesful html alignment should have created html/html.html",
        )

        with open(join(output, "html.html"), "rb") as fhtml:
            path_bytes = fhtml.read()
        htmldoc = fromstring(path_bytes)
        b64_pattern = r"data:[\w\/\+]*;base64,\w*"
        self.assertRegex(
            htmldoc.body.xpath("//read-along")[0].attrib["text"], b64_pattern
        )
        self.assertRegex(
            htmldoc.body.xpath("//read-along")[0].attrib["alignment"], b64_pattern
        )
        self.assertRegex(
            htmldoc.body.xpath("//read-along")[0].attrib["audio"], b64_pattern
        )

    def test_permission_denied(self):
        # This test is not stable, just disable it.
        # It apparently also does not work correctly on M1 Macs either, even in Docker.
        return

        import platform

        if platform.system() == "Windows" or "WSL2" in platform.release():
            # Cannot change the permission on a directory in Windows though
            # os.mkdir() or os.chmod(), so skip this test
            return
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

    def test_bad_anchors(self):
        xml_text = """<?xml version='1.0' encoding='utf-8'?>
            <TEI><text xml:lang="fra"><body><p>
            <anchor /><s>Bonjour.</s><anchor time="invalid"/>
            </p></body></text></TEI>
        """
        xml_file = join(self.tempdir, "bad-anchor.xml")
        with open(xml_file, "w", encoding="utf8") as f:
            print(xml_text, file=f)
        bad_anchors_result = self.runner.invoke(
            align,
            [
                xml_file,
                join(self.data_dir, "noise.mp3"),
                join(self.tempdir, "out-bad-anchors"),
            ],
        )
        for msg in [
            'missing "time" attribute',
            'invalid "time" attribute "invalid"',
            "Could not parse all anchors",
            "Aborting.",
        ]:
            self.assertIn(msg, bad_anchors_result.stdout)


if __name__ == "__main__":
    main()
