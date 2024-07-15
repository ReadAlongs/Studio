#!/usr/bin/env python

"""
Unit test suite for the readalongs align CLI command
"""

import os
import tempfile
from os.path import exists, join
from pathlib import Path
from unittest import main

from basic_test_case import BasicTestCase
from lxml.html import fromstring
from sound_swallower_stub import SoundSwallowerStub

from readalongs._version import READALONG_FILE_FORMAT_VERSION, VERSION
from readalongs.cli import align, langs


def write_file(filename: str, file_contents: str) -> str:
    """Write file_contents to file filename, and return its name (filename)"""
    with open(filename, mode="w", encoding="utf8") as f:
        f.write(file_contents)
    return filename


class TestAlignCli(BasicTestCase):
    """Unit test suite for the readalongs align CLI command"""

    def test_invoke_align(self):
        """Basic readalongs align invocation and some variants"""
        output = self.tempdir / "output"
        with open("image-for-page1.jpg", "wb"):
            pass
        # Run align from plain text
        results = self.runner.invoke(
            align,
            [
                "-s",
                "-o",
                "vtt",
                "-o",  # tests that we can use -o more than once
                "srt:TextGrid,eaf",  # tests that we can give -o multiple values, separated by : or ,
                "-l",
                "fra",
                "--align-mode",
                "auto",
                "--config",
                join(self.data_dir, "sample-config.json"),
                self.add_bom(join(self.data_dir, "ej-fra.txt")),
                join(self.data_dir, "ej-fra.m4a"),
                str(output),
            ],
        )
        # print(results.output)
        self.assertEqual(results.exit_code, 0)
        expected_output_files = [
            "www/output.readalong",
            "www/output.m4a",
            "www/index.html",
            "output.TextGrid",
            "output.eaf",
            "output_sentences.srt",
            "output_sentences.vtt",
            "output_words.srt",
            "output_words.vtt",
            "www/readme.txt",
        ]
        for f in expected_output_files:
            self.assertTrue(
                (output / f).exists(), f"successful alignment should have created {f}"
            )
        with open(output / "www/index.html", encoding="utf8") as f:
            self.assertIn(
                '<read-along href="output.readalong" audio="output.m4a"',
                f.read(),
            )
        self.assertTrue(
            (output / "tempfiles/output.tokenized.readalong").exists(),
            "alignment with -s should have created tempfiles/output.tokenized.readalong",
        )
        with open(
            output / "tempfiles/output.tokenized.readalong",
            "r",
            encoding="utf-8",
        ) as f:
            self.assertNotIn("\ufeff", f.read())
        self.assertTrue(
            (output / "www/assets/image-for-page1.jpg").exists(),
            "alignment with image files should have copied image-for-page1.jpg to assets",
        )
        self.assertIn("image-for-page2.jpg is accessible ", results.stdout)
        os.unlink("image-for-page1.jpg")
        self.assertFalse(exists("image-for-page1.jpg"))
        self.assertIn("Align mode strict succeeded for sequence 0.", results.stdout)
        # print(results.stdout)

        # Move the alignment output to compare with further down
        # We cannot just output to a different name because changing the output file name
        # changes the contents of the output.
        output1 = str(output) + "1"
        os.rename(output, output1)
        self.assertFalse(output.exists(), "os.rename() should have moved dir")

        # Run align again, but on an XML input file with various added DNA text
        results_dna = self.runner.invoke(
            align,
            [
                "-o",
                "xhtml",
                "--align-mode",
                "moderate",
                "-s",
                "--config",
                join(self.data_dir, "sample-config.json"),
                self.add_bom(join(self.data_dir, "ej-fra-dna.readalong")),
                join(self.data_dir, "ej-fra.m4a"),
                str(output),
            ],
        )
        self.assertEqual(results_dna.exit_code, 0)
        # print(results_dna.stdout)
        self.assertTrue(
            (output / "www/output.readalong").exists(),
            "successful alignment with DNA should have created output.readalong",
        )
        self.assertTrue(
            (output / "output.xhtml").exists(),
            "successful alignment with -o xhtml should have created output.xhtml",
        )
        self.assertIn("Please copy image-for-page1.jpg to ", results_dna.stdout)
        self.assertFalse(
            (output / "www/assets/image-for-page1.jpg").exists(),
            "image-for-page1.jpg was not on disk, cannot have been copied",
        )
        self.assertIn(
            "Align mode moderate succeeded for sequence 0.", results_dna.stdout
        )

        # We test error situations in the same test case, since we reuse the same outputs
        results_output_exists = self.runner.invoke(
            align,
            [
                join(self.data_dir, "ej-fra-dna.readalong"),
                join(self.data_dir, "ej-fra.m4a"),
                str(output),
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
                join(self.data_dir, "ej-fra-dna.readalong"),
                join(self.data_dir, "ej-fra.m4a"),
                str(output / "www/output.readalong"),
            ],
        )
        self.assertNotEqual(results_output_is_regular_file, 0)
        self.assertIn(
            "already exists but is a not a directory",
            results_output_is_regular_file.output,
        )

    def test_align_with_package(self):
        """Test creating a single-file package, with -o html"""

        output = join(self.tempdir, "html")
        with SoundSwallowerStub("t0b0d0p0s0w0:920:1620", "t0b0d0p0s1w0:1620:1690"):
            results_html = self.runner.invoke(
                align,
                [
                    join(self.data_dir, "ej-fra-package.readalong"),
                    join(self.data_dir, "ej-fra.m4a"),
                    output,
                    "-o",
                    "html",
                    "--config",
                    self.add_bom(self.data_dir / "sample-config.json"),
                ],
            )
        # print(results_html.output)
        self.assertEqual(results_html.exit_code, 0)
        self.assertTrue(
            exists(join(output, "Offline-HTML", "html.html")),
            "successful html alignment should have created html/Offline-HTML/html.html",
        )

        with open(join(output, "Offline-HTML", "html.html"), "rb") as fhtml:
            path_bytes = fhtml.read()
        htmldoc = fromstring(path_bytes)
        b64_pattern = r"data:[\w\/\-\+]*;base64,\w*"
        self.assertRegex(
            htmldoc.body.xpath("//read-along")[0].attrib["href"], b64_pattern
        )
        self.assertRegex(
            htmldoc.body.xpath("//read-along")[0].attrib["audio"], b64_pattern
        )

    def not_test_permission_denied(self):
        """Non-portable test to make sure denied permission triggers an error -- disabled"""
        # This test is not stable, just disable it.
        # It apparently does not work correctly on M1 Macs either, even in Docker.

        import platform

        if platform.system() == "Windows" or "WSL2" in platform.release():
            # Cannot change the permission on a directory in Windows though
            # os.mkdir() or os.chmod(), so skip this test
            return
        dirname = join(self.tempdir, "permission_denied")
        os.mkdir(dirname, mode=0o444)
        results = self.runner.invoke(
            align,
            [
                "-f",
                join(self.data_dir, "ej-fra-dna.readalong"),
                join(self.data_dir, "ej-fra.m4a"),
                dirname,
            ],
        )
        self.assertNotEqual(results, 0)
        self.assertIn("Cannot write into output folder", results.output)

    def test_langs_cmd(self):
        """Validates that readalongs langs lists all in-langs that can map to eng-arpabet"""
        results = self.runner.invoke(langs)
        self.assertEqual(results.exit_code, 0)
        self.assertIn("crg-tmd", results.stdout)
        self.assertIn("crg-dv ", results.stdout)
        self.assertNotIn("crg ", results.stdout)
        self.assertNotIn("fn-unicode", results.stdout)

    def test_align_english(self):
        """Validates that the lexicon-based g2p works for English language alignment"""

        input_filename = write_file(
            join(self.tempdir, "input"),
            "This is some text that we will run through the English lexicon "
            "grapheme to morpheme approach.",
        )
        output_dir = join(self.tempdir, "eng-output")
        # Run align from plain text
        with SoundSwallowerStub("word:0:1000"):
            self.runner.invoke(
                align,
                [
                    "-s",
                    "-l",
                    "eng",
                    input_filename,
                    join(self.data_dir, "ej-fra.m4a"),
                    output_dir,
                ],
            )

        g2p_ref = "".join(
            (
                '<s id="t0b0d0p0s0">',
                '<w id="t0b0d0p0s0w0" ARPABET="DH IH S">This</w> ',
                '<w id="t0b0d0p0s0w1" ARPABET="IH Z">is</w> ',
                '<w id="t0b0d0p0s0w2" ARPABET="S AH M">some</w> ',
                '<w id="t0b0d0p0s0w3" ARPABET="T EH K S T">text</w> ',
                '<w id="t0b0d0p0s0w4" ARPABET="DH AE T">that</w> ',
                '<w id="t0b0d0p0s0w5" ARPABET="W IY">we</w> ',
                '<w id="t0b0d0p0s0w6" ARPABET="W IH L">will</w> ',
                '<w id="t0b0d0p0s0w7" ARPABET="R AH N">run</w> ',
                '<w id="t0b0d0p0s0w8" ARPABET="TH R UW">through</w> ',
                '<w id="t0b0d0p0s0w9" ARPABET="DH AH">the</w> ',
                '<w id="t0b0d0p0s0w10" ARPABET="IH NG G L IH SH">English</w> ',
                '<w id="t0b0d0p0s0w11" ARPABET="L EH K S IH K AA N">lexicon</w> ',
                '<w id="t0b0d0p0s0w12" effective-g2p-lang="und" ARPABET="G D AA P HH EY M EY">grapheme</w> ',
                '<w id="t0b0d0p0s0w13" ARPABET="T UW">to</w> ',
                '<w id="t0b0d0p0s0w14" effective-g2p-lang="und" ARPABET="M OW D P HH EY M EY">morpheme</w> ',
                '<w id="t0b0d0p0s0w15" ARPABET="AH P R OW CH">approach</w>',
                ".</s>",
            )
        )

        tokenized_file = join(
            self.tempdir, "eng-output", "tempfiles", "eng-output.g2p.readalong"
        )
        with open(tokenized_file, "r", encoding="utf8") as f:
            tok_output = f.read()

        self.assertIn(g2p_ref, tok_output)

    def test_invalid_config(self):
        """unit testing for invalid config specifications"""

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
        with open(config_file, "w", encoding="utf8") as f:
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
        """Make sure invalid anchors yield appropriate errors"""

        xml_text = """<?xml version='1.0' encoding='utf-8'?>
            <read-along version="%s"><meta name="generator" content="@readalongs/studio (cli) %s"/><text xml:lang="fra"><body><p>
            <anchor /><s>Bonjour.</s><anchor time="invalid"/>
            </p></body></text></read-along>
        """ % (
            READALONG_FILE_FORMAT_VERSION,
            VERSION,
        )
        xml_file = join(self.tempdir, "bad-anchor.readalong")
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

    def test_misc_align_errors(self):
        """Test calling readalongs align with misc CLI errors"""
        results = self.runner.invoke(
            align,
            [
                join(self.data_dir, "ej-fra.txt"),
                join(self.data_dir, "ej-fra.m4a"),
                join(self.tempdir, "out-missing-l"),
            ],
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("No input language specified", results.output)

        with SoundSwallowerStub("[NOISE]:0:1"):
            results = self.runner.invoke(
                align,
                [
                    join(self.data_dir, "fra-prepared.readalong"),
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "noise-only"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("produced 0 segments", results.output)

        with SoundSwallowerStub(
            "[NOISE]:0:1", "w0:1:1000", "<sil>:1000:1100", "w1:1100:2000"
        ):
            results = self.runner.invoke(
                align,
                [
                    join(self.data_dir, "ej-fra.readalong"),
                    join(self.data_dir, "ej-fra.m4a"),
                    join(self.tempdir, "two-words"),
                ],
            )
        # print(results.output)
        # We don't check results.exit_code since that's a soft warning, not a hard error
        self.assertIn("produced 2 segments", results.output)
        self.assertIn(
            "Alignment produced a different number of segments and tokens than were in the input.",
            results.output,
        )

    def test_infer_plain_text_or_xml(self):
        """align -i is obsolete, now we infer plain text vs XML; test that!"""

        # plain text with guess by contents
        infile1 = write_file(join(self.tempdir, "infile1"), "some plain text")
        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    infile1,
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir1"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        # This error message confirms it's being processed as plain text
        self.assertIn("No input language specified for plain text", results.output)

        # plain text by extension
        infile2 = write_file(join(self.tempdir, "infile2.txt"), "<?xml but .txt")
        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    infile2,
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir2"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        # This error message confirms it's being processed as plain text
        self.assertIn("No input language specified for plain text", results.output)

        # XML with guess by contents
        infile3 = self.add_bom(
            write_file(
                join(self.tempdir, "infile3"),
                "<?xml version='1.0' encoding='utf-8'?><text>blah blah</text>",
            )
        )
        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    infile3,
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir3"),
                ],
            )
        self.assertEqual(results.exit_code, 0)

        # XML with guess by contents, but with content error
        infile4 = write_file(
            join(self.tempdir, "infile4"),
            "<?xml version='1.0' encoding='utf-8'?><text>blah blah</bad_tag>",
        )
        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    infile4,
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir4"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Error parsing XML", results.output)

        # XML by file extension
        infile5 = write_file(join(self.tempdir, "infile5.readalong"), "Not XML!")
        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    infile5,
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir5"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Error parsing XML", results.output)

    def test_obsolete_switches(self):
        # Giving -i switch generates an obsolete-switch error message
        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    "-i",
                    join(self.data_dir, "fra.txt"),
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir6"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("is obsolete.", results.output)

        # Giving --g2p-verbose switch generates an obsolete-switch error message
        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    "--g2p-verbose",
                    join(self.data_dir, "fra.txt"),
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir7"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("is obsolete.", results.output)

        # Giving --g2p-fallback switch generates an obsolete-switch error message
        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    "--g2p-fallback",
                    "fra:end:und",
                    join(self.data_dir, "fra.txt"),
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir8"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("is obsolete.", results.output)

    def test_oo_option(self):
        """Exercise the hidden -oo / --output-orth option"""
        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    "-oo",
                    "eng-arpabet",
                    join(self.data_dir, "ej-fra.readalong"),
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir9"),
                ],
            )
        self.assertEqual(results.exit_code, 0)

        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    "-oo",
                    "not-an-alphabet",
                    join(self.data_dir, "ej-fra.readalong"),
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir10"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Could not g2p", results.output)
        self.assertIn("not-an-alphabet", results.output)

        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    "-oo",
                    "dan-ipa",
                    join(self.data_dir, "ej-fra.readalong"),
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir11"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Could not g2p", results.output)
        self.assertIn("no path", results.output)

        with SoundSwallowerStub("word:0:1"):
            results = self.runner.invoke(
                align,
                [
                    "-oo",
                    "dan-ipa",
                    "-l",
                    "eng",
                    join(self.data_dir, "fra.txt"),
                    join(self.data_dir, "noise.mp3"),
                    join(self.tempdir, "outdir12"),
                ],
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Could not g2p", results.output)
        self.assertIn('no path from "eng" to ', results.output)

    def add_bom(self, filename):
        """Create a temporary copy of filename with the a BOM in it, in self.tempdir"""
        # We pepper calls to add_bom() around the test suite, to make sure all
        # different kinds of input files are accepted with and without a BOM
        output_file = tempfile.NamedTemporaryFile(
            mode="wb",
            dir=self.tempdir,
            delete=False,
            prefix="bom_",
            suffix=os.path.basename(filename),
        )
        output_file.write(b"\xef\xbb\xbf")
        with open(filename, "rb") as file_binary:
            output_file.write(file_binary.read())
        output_file.close()
        return output_file.name

    def test_add_bom(self):
        """Make sure add_bom does what we mean it to, i.e., test the test harness."""

        def slurp_bin(filename):
            with open(filename, "rb") as f:
                return f.read()

        def slurp_text(filename, encoding):
            with open(filename, "r", encoding=encoding) as f:
                return f.read()

        base_file = write_file(self.tempdir / "add-bom-input.txt", "Random Text été")
        bom_file = self.add_bom(base_file)
        self.assertEqual(
            slurp_text(base_file, "utf-8"), slurp_text(bom_file, "utf-8-sig")
        )
        self.assertEqual(
            slurp_text(bom_file, "utf-8"), "\ufeff" + slurp_text(base_file, "utf-8")
        )
        self.assertNotEqual(slurp_bin(base_file), slurp_bin(bom_file))
        self.assertEqual(b"\xef\xbb\xbf" + slurp_bin(base_file), slurp_bin(bom_file))

        bom_file_pathlib = self.add_bom(Path(base_file))
        self.assertEqual(
            slurp_text(base_file, "utf-8"), slurp_text(bom_file_pathlib, "utf-8-sig")
        )


if __name__ == "__main__":
    main()
