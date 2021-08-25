#!/usr/bin/env python3

import io
import os
import tempfile
from unittest import TestCase, main

from lxml import etree

from readalongs.align import align_audio
from readalongs.app import app
from readalongs.cli import align, g2p, prepare, tokenize
from readalongs.text.convert_xml import convert_xml


class TestG2pCli(TestCase):
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    # Set this to True to keep the temp dirs after running, for manual inspection
    # but please don't push a commit setting this to True!
    keep_temp_dir_after_running = False
    # Set this to True to display the output of many commands invoked here, for building
    # and debugging this test suite
    show_invoke_output = False

    def setUp(self):
        app.logger.setLevel("DEBUG")
        self.runner = app.test_cli_runner()
        if not self.keep_temp_dir_after_running:
            # Temporary directories that get automatically cleaned up:
            self.tempdirobj = tempfile.TemporaryDirectory(
                prefix="tmpdir_test_g2p_cli_", dir="."
            )
            self.tempdir = self.tempdirobj.name
        else:
            # Alternative tempdir code keeps it after running, for manual inspection:
            self.tempdir = tempfile.mkdtemp(prefix="tmpdir_test_g2p_cli_", dir=".")
            print("tmpdir={}".format(self.tempdir))

    def tearDown(self):
        if not self.keep_temp_dir_after_running:
            self.tempdirobj.cleanup()

    def test_invoke_g2p(self):
        input_file = os.path.join(self.data_dir, "fra-tokenized.xml")
        g2p_file = os.path.join(self.tempdir, "fra-g2p.xml")
        results = self.runner.invoke(g2p, [input_file, g2p_file])
        # print(f"g2p results.output='{results.output}'")
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, "fra-g2p.xml")))

        # Testing that it fails when the file already exists has to be in the same test,
        # otherwise we have a different tempdir and the file won't already exist
        results = self.runner.invoke(g2p, [input_file, g2p_file])
        # print(f"g2p results.output='{results.output}'")
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("use -f to overwrite", results.output)

        # And add -f to force the overwrite
        results = self.runner.invoke(g2p, ["-f", input_file, g2p_file])
        # print(f"g2p results.output='{results.output}'")
        self.assertEqual(results.exit_code, 0)

    def test_bad_fallback_lang(self):
        input_file = os.path.join(self.data_dir, "fra-tokenized.xml")
        results = self.runner.invoke(
            g2p, ["--g2p-fallback=fra:notalang:und", input_file, "-"]
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Invalid value: g2p fallback lang", results.output)

    def test_bad_xml_input(self):
        input_file = os.path.join(self.data_dir, "ej-fra.txt")
        results = self.runner.invoke(g2p, ["--debug", input_file, "-"])
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Error parsing input file", results.output)

    def test_mixed_langs(self):
        input_file = os.path.join(self.data_dir, "mixed-langs.tokenized.xml")
        g2p_file = os.path.join(self.tempdir, "mixed-langs.g2p.xml")
        results = self.runner.invoke(g2p, [input_file, g2p_file])
        # print(f"g2p results.output='{results.output}'")
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(g2p_file))

        ref_file = os.path.join(self.data_dir, "mixed-langs.g2p.xml")
        with open(g2p_file) as output_f, open(ref_file) as ref_f:
            self.maxDiff = None
            self.assertListEqual(
                list(output_f),
                list(ref_f),
                f"output {g2p_file} and reference {ref_file} differ.",
            )

    # Write text to a temp file, pass it through prepare -l lang, and then tokenize,
    # saving the final results into filename.
    # filename is assumed to be inside self.tempdir, so we count on tearDown() to clean up.
    def write_prepare_tokenize(self, text, lang, filename):
        with open(filename + ".input.txt", "w", encoding="utf8") as f:
            print(text, file=f)
        self.runner.invoke(
            prepare, ["-l", lang, filename + ".input.txt", filename + ".prepared.xml"]
        )
        self.runner.invoke(tokenize, [filename + ".prepared.xml", filename])

    def test_english_oov(self):
        tok_file = os.path.join(self.tempdir, "tok.xml")
        self.write_prepare_tokenize("This is a froobnelicious OOV.", "eng", tok_file)
        results = self.runner.invoke(g2p, [tok_file])
        if self.show_invoke_output:
            print(
                f"test_english_oov: g2p "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("could not be g2p", results.output)
        # self.assertTrue(isinstance(results.exception, KeyError))

        # with a fall back to und, it works
        results = self.runner.invoke(g2p, ["--g2p-fallback", "und", tok_file, "-"])
        if self.show_invoke_output:
            print(
                f"test_english_oov with fallback: g2p "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertEqual(results.exit_code, 0)

    def test_french_oov(self):
        tok_file = os.path.join(self.tempdir, "tok.xml")
        g2p_file = os.path.join(self.tempdir, "g2p.xml")
        self.write_prepare_tokenize(
            "Le ñ n'est pas dans l'alphabet français.", "fra", tok_file
        )
        results = self.runner.invoke(g2p, [tok_file, g2p_file])
        if self.show_invoke_output:
            print(
                f"test_french_oov: g2p "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("could not be g2p", results.output)

        # with a fall back to und, it works
        g2p_file2 = os.path.join(self.tempdir, "g2p-fallback.xml")
        results = self.runner.invoke(
            g2p, ["--g2p-fallback", "und", tok_file, g2p_file2]
        )
        if self.show_invoke_output:
            print(
                f"test_french_oov with fallback: g2p "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertEqual(results.exit_code, 0)

    def test_three_way_fallback(self):
        tok_file = os.path.join(self.tempdir, "text.tokenized.xml")
        g2p_file = os.path.join(self.tempdir, "text.g2p.xml")
        self.write_prepare_tokenize(
            "In French été works but Nunavut ᓄᓇᕗᑦ does not.", "eng", tok_file
        )
        # Here we also test generating the output filename from the input filename
        results = self.runner.invoke(g2p, ["--g2p-fallback", "fra:iku", tok_file])
        if self.show_invoke_output:
            print(
                f"test_three_way_fallback: g2p "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(g2p_file))
        self.assertNotIn("not recognized as IPA", results.output)
        self.assertNotIn("not fully valid eng-arpabet", results.output)

        # Run with verbose output and look for the warning messages
        results = self.runner.invoke(
            g2p,
            ["--g2p-fallback=fra:iku", "--g2p-verbose", tok_file, g2p_file + "verbose"],
        )
        if self.show_invoke_output:
            print(
                f"test_three_way_fallback: g2p "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertEqual(results.exit_code, 0)
        self.assertIn("not recognized as IPA", results.output)
        self.assertIn("not fully valid eng-arpabet", results.output)

        # this text also works with "und", now that we use unidecode
        results = self.runner.invoke(g2p, ["--g2p-fallback=und", tok_file, "-"])
        self.assertEqual(results.exit_code, 0)
        self.assertIn("Trying fallback: und", results.output)

    def test_align_with_error(self):
        text_file = os.path.join(self.tempdir, "input.txt")
        with io.open(text_file, "w", encoding="utf8") as f:
            print("In French été works but Nunavut ᓄᓇᕗᑦ does not.", file=f)
        empty_wav = os.path.join(self.tempdir, "empty.wav")
        with io.open(empty_wav, "wb"):
            pass
        output_dir = os.path.join(self.tempdir, "aligned")
        results = self.runner.invoke(
            align, ["-l", "eng", "-i", text_file, empty_wav, output_dir]
        )
        if self.show_invoke_output:
            print(
                f"align with wrong language: "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("could not be g2p", results.output)

        results = self.runner.invoke(
            align,
            [
                "-l",
                "eng",
                "-i",
                "-f",
                "--g2p-fallback=fra:iku",
                text_file,
                empty_wav,
                output_dir,
            ],
        )
        if self.show_invoke_output:
            print(
                f"align with wrong language, plus fallback: "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertIn("Trying fallback: fra", results.output)
        self.assertIn("Trying fallback: iku", results.output)
        # We get the error about reading the audio file only if g2p succeeded:
        self.assertIn("Error reading audio file", results.output)

    def test_with_stdin(self):
        input_file = os.path.join(self.data_dir, "fra-tokenized.xml")
        with io.open(input_file, encoding="utf8") as f:
            inputtext = f.read()
        results = self.runner.invoke(g2p, "-", input=inputtext)
        self.assertEqual(results.exit_code, 0)
        self.assertIn("S AH S IY", results.output)

    def test_align_with_invalid_preg2p(self):
        txt = """<document><s xml:lang="und">
            <w>word</w>
            <w ARPABET="G OW D">good</w>
            <w ARPABET="NOT ARPABET">error</w>
        </s></document>"""
        input_file = os.path.join(self.tempdir, "pre-g2p.xml")
        with open(input_file, "w") as f:
            print(txt, file=f)

        results = self.runner.invoke(g2p, [input_file, "-"])
        self.assertNotEqual(results.exit_code, 0)
        # print(results.output)
        self.assertIn("could not be g2p", results.output)
        self.assertIn('<w id="s0w0" ARPABET="W OW D D">word</w>', results.output)
        self.assertIn('<w ARPABET="G OW D" id="s0w1">good</w>', results.output)
        self.assertIn('<w ARPABET="NOT ARPABET" id="s0w2">error</w>', results.output)

        audio_file = os.path.join(self.data_dir, "ej-fra.m4a")
        with self.assertRaises(RuntimeError) as e:
            results = align_audio(input_file, audio_file)
        self.assertIn("could not be g2p'd", str(e.exception))

    def test_align_with_preg2p(self):
        text_file = os.path.join(self.data_dir, "mixed-langs.tokenized.xml")
        audio_file = os.path.join(self.data_dir, "ej-fra.m4a")
        _ = align_audio(
            text_file, audio_file, save_temps=os.path.join(self.tempdir, "foo")
        )
        with open(os.path.join(self.tempdir, "foo.dict"), "r") as f:
            dict_file = f.read()
            self.assertIn("D G IY T UW P IY D", dict_file)

    def run_convert_xml(self, str):
        return etree.tounicode(convert_xml(etree.fromstring(str))[0])

    def test_convert_xml(self):
        self.assertEqual(
            self.run_convert_xml("<t><w>word</w><w></w><n>not word</n></t>"),
            '<t><w ARPABET="W OW D D">word</w><w/><n>not word</n></t>',
        )

        self.assertEqual(
            self.run_convert_xml(
                '<s><w xml:lang="eng">Patrick</w><w xml:lang="kwk-umista">xtła̱n</w></s>'
            ),
            '<s><w xml:lang="eng" ARPABET="P AE T R IH K">Patrick</w><w xml:lang="kwk-umista" ARPABET="K Y T S AH N">xtła̱n</w></s>',
        )

        self.assertEqual(
            self.run_convert_xml('<s><w xml:lang="und">Patrickxtła̱n</w></s>'),
            '<s><w xml:lang="und" ARPABET="P AA T D IY CH K K T L AA N">Patrickxtła̱n</w></s>',
        )

    def test_convert_xml_invalid(self):
        xml = etree.fromstring('<s><w ARPABET="V AA L IY D">valid</w></s>')
        c_xml, valid = convert_xml(xml)
        self.assertEqual(
            etree.tounicode(c_xml), '<s><w ARPABET="V AA L IY D">valid</w></s>'
        )
        self.assertTrue(valid, "convert_xml with valid pre-g2p'd text")

        xml = etree.fromstring('<s><w ARPABET="invalid">invalid</w></s>')
        c_xml, valid = convert_xml(xml)
        self.assertEqual(
            etree.tounicode(c_xml), '<s><w ARPABET="invalid">invalid</w></s>'
        )
        self.assertFalse(valid, "convert_xml with invalid pre-g2p'd text")


if __name__ == "__main__":
    main()
