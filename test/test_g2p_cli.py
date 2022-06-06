#!/usr/bin/env python3

"""Test suite for the readalongs g2p CLI command"""

import os
from unittest import main

from basic_test_case import BasicTestCase
from lxml import etree
from sound_swallower_stub import SoundSwallowerStub

from readalongs.align import align_audio
from readalongs.cli import align, g2p, prepare, tokenize
from readalongs.log import LOGGER
from readalongs.text.convert_xml import convert_xml


class TestG2pCli(BasicTestCase):
    """Test suite for the readalongs g2p CLI command"""

    # Set this to True to display the output of many commands invoked here, for building
    # and debugging this test suite
    show_invoke_output = False

    def test_invoke_g2p(self):
        """Basic invocation of readalongs g2p"""
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

    def test_bad_xml_input(self):
        """readalongs g2p with invalid XML input"""
        input_file = os.path.join(self.data_dir, "ej-fra.txt")
        results = self.runner.invoke(g2p, ["--debug", input_file, "-"])
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Error parsing input file", results.output)

    def test_mixed_langs(self):
        """readalongs g2p with an input containing multiple languages"""
        input_file = os.path.join(self.data_dir, "mixed-langs.tokenized.xml")
        g2p_file = os.path.join(self.tempdir, "mixed-langs.g2p.xml")
        results = self.runner.invoke(g2p, [input_file, g2p_file])
        # print(f"g2p results.output='{results.output}'")
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(g2p_file))

        ref_file = os.path.join(self.data_dir, "mixed-langs.g2p.xml")
        with open(g2p_file, encoding="utf8") as output_f, open(
            ref_file, encoding="utf8"
        ) as ref_f:
            self.maxDiff = None
            self.assertListEqual(
                list(output_f),
                list(ref_f),
                f"output {g2p_file} and reference {ref_file} differ.",
            )

    def test_invoke_with_obsolete_switches(self):
        """Using obsolete options should yield a helpful error message"""

        input_file = os.path.join(self.data_dir, "fra-tokenized.xml")
        g2p_file = os.path.join(self.tempdir, "obsolete1.xml")
        results = self.runner.invoke(
            g2p, ["--g2p-fallback", "fra:und", input_file, g2p_file]
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("is obsolete", results.output)

        g2p_file = os.path.join(self.tempdir, "obsolete2.xml")
        results = self.runner.invoke(g2p, ["--g2p-verbose", input_file, g2p_file])
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("is obsolete", results.output)

    # Write text to a temp file, pass it through prepare -l lang, and then tokenize,
    # saving the final results into filename.
    # filename is assumed to be inside self.tempdir, so we count on tearDown() to clean up.
    def write_prepare_tokenize(self, text, lang, filename):
        """Create the input file for some test cases in this suite"""
        with open(filename + ".input.txt", "w", encoding="utf8") as f:
            print(text, file=f)
        self.runner.invoke(
            prepare,
            [
                "-l",
                lang,
                "--lang-no-append-und",
                filename + ".input.txt",
                filename + ".prepared.xml",
            ],
        )
        self.runner.invoke(tokenize, [filename + ".prepared.xml", filename])

    def test_english_oov(self):
        """readalongs g2p should handle English OOVs correctly"""
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
        tok_file_with_fallback = os.path.join(self.tempdir, "fallback.xml")
        self.write_prepare_tokenize(
            "This is a froobnelicious OOV.", "eng:und", tok_file_with_fallback
        )
        results = self.runner.invoke(g2p, [tok_file_with_fallback, "-"])
        if self.show_invoke_output:
            print(
                f"test_english_oov with fallback: g2p "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertEqual(results.exit_code, 0)

    def test_french_oov(self):
        """readalongs g2p should handle French OOVs correctly"""
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
        tok_file2 = os.path.join(self.tempdir, "tok2.xml")
        self.write_prepare_tokenize(
            "Le ñ n'est pas dans l'alphabet français.", "fra:und", tok_file2
        )
        g2p_file2 = os.path.join(self.tempdir, "g2p-fallback.xml")
        results = self.runner.invoke(g2p, [tok_file2, g2p_file2])
        if self.show_invoke_output:
            print(
                f"test_french_oov with fallback: g2p "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertEqual(results.exit_code, 0)

    def test_three_way_fallback(self):
        """readalongs g2p --g2p-fallback with multi-step cascades"""
        tok_file = os.path.join(self.tempdir, "text.tokenized.xml")
        g2p_file = os.path.join(self.tempdir, "text.g2p.xml")
        self.write_prepare_tokenize(
            "In French été works but Nunavut ᓄᓇᕗᑦ does not.", "eng:fra:iku", tok_file
        )
        # Here we also test generating the output filename from the input filename
        results = self.runner.invoke(g2p, [tok_file])
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
            g2p, ["--debug-g2p", tok_file, g2p_file + "verbose"]
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
        tok_file2 = os.path.join(self.tempdir, "text.tokenized2.xml")
        self.write_prepare_tokenize(
            "In French été works but Nunavut ᓄᓇᕗᑦ does not.", "eng:und", tok_file2
        )
        results = self.runner.invoke(g2p, [tok_file2, "-"])
        self.assertEqual(results.exit_code, 0)
        self.assertIn("Trying fallback: und", results.output)

    def test_align_with_error(self):
        """handling g2p errors in readalongs align with --g2p-fallback"""
        text_file = os.path.join(self.tempdir, "input.txt")
        with open(text_file, "w", encoding="utf8") as f:
            print("In French été works but Nunavut ᓄᓇᕗᑦ does not.", file=f)
        empty_wav = os.path.join(self.tempdir, "empty.wav")
        with open(empty_wav, "wb"):
            pass
        output_dir = os.path.join(self.tempdir, "aligned")
        results = self.runner.invoke(
            align,
            ["-l", "eng", text_file, empty_wav, output_dir, "--lang-no-append-und"],
        )
        if self.show_invoke_output:
            print(
                f"align with wrong language: "
                f"results.output='{results.output}' "
                f"results.exception={results.exception!r}"
            )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("could not be g2p", results.output)
        self.assertNotIn("Number of aligned segments", results.output)

        with SoundSwallowerStub("t0b0d0p0s0w0:920:1620", "t0b0d0p0s1w0:1620:1690"):
            results = self.runner.invoke(
                align,
                [
                    "-l",
                    "eng",  # lang 1 is eng
                    "-f",
                    "--language=fra:iku",  # fallback langs are fra and iku
                    text_file,
                    os.path.join(self.data_dir, "noise.mp3"),
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
        self.assertNotIn("could not be g2p", results.output)
        self.assertIn("Number of aligned segments", results.output)

    def test_with_stdin(self):
        """readalongs g2p running with stdin as input"""
        input_file = os.path.join(self.data_dir, "fra-tokenized.xml")
        with open(input_file, encoding="utf8") as f:
            inputtext = f.read()
        results = self.runner.invoke(g2p, "-", input=inputtext)
        self.assertEqual(results.exit_code, 0)
        self.assertIn("S AH S IY", results.output)

    def test_align_with_invalid_preg2p(self):
        """readalongs g2p gracefully handling wrong inputs"""
        txt = """<document><s xml:lang="und">
            <w>word</w>
            <w ARPABET="G OW D">good</w>
            <w ARPABET="NOT ARPABET">error</w>
        </s></document>"""
        input_file = os.path.join(self.tempdir, "pre-g2p.xml")
        with open(input_file, "w", encoding="utf8") as f:
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
        """readalongs align working on previously g2p'd text"""
        text_file = os.path.join(self.data_dir, "mixed-langs.tokenized.xml")
        audio_file = os.path.join(self.data_dir, "ej-fra.m4a")
        with SoundSwallowerStub("t0b0d0p0s0w0:920:1620", "t0b0d0p0s1w0:1620:1690"):
            _ = align_audio(
                text_file, audio_file, save_temps=os.path.join(self.tempdir, "foo")
            )
        with open(os.path.join(self.tempdir, "foo.dict"), "r", encoding="utf8") as f:
            dict_file = f.read()
            self.assertIn("S AH S IY", dict_file)  # "ceci" in fra
            self.assertIn("DH IH S", dict_file)  # "this" in eng
            self.assertIn("HH EH Y", dict_file)  # "Hej" in dan
            self.assertIn("D G IY T UW P IY D", dict_file)  # pre-g2p'd OOV

    def run_convert_xml(self, input_string):
        """wrap convert_xml to make unit testing easier"""
        return etree.tounicode(convert_xml(etree.fromstring(input_string))[0])

    def test_convert_xml(self):
        """unit testing for readalongs.text.convert_xml.convert_xml()

        convert_xml() is the inner method in readalongs that calls g2p.
        It's not very well named, but it still needs unit testing. :)
        """
        self.assertEqual(
            self.run_convert_xml("<t><w>word</w><w></w><n>not word</n></t>"),
            '<t><w ARPABET="W OW D D">word</w><w/><n>not word</n></t>',
        )

        self.assertEqual(
            self.run_convert_xml(
                '<s><w xml:lang="eng">Patrick</w><w xml:lang="kwk-umista">xtła̱n</w></s>'
            ),
            '<s><w xml:lang="eng" ARPABET="P AE T R IH K">Patrick</w>'
            '<w xml:lang="kwk-umista" ARPABET="K Y T S AH N">xtła̱n</w></s>',
        )

        self.assertEqual(
            self.run_convert_xml('<s><w xml:lang="und">Patrickxtła̱n</w></s>'),
            '<s><w xml:lang="und" ARPABET="P AA T D IY CH K K T L AA N">Patrickxtła̱n</w></s>',
        )

    def test_convert_xml_invalid(self):
        """test readalongs.text.convert_xml.convert_xml() with invalid input"""
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

    def test_invalid_langs_in_xml(self):
        xml = etree.fromstring(
            """
            <s>
            <w lang="eng" fallback-langs="foo">français falls back to invalid foo</w>
            <w lang="crx-syl">no path to arpabet</w>
            </s>
        """
        )
        with self.assertLogs(LOGGER, level="WARNING") as cm:
            c_xml, valid = convert_xml(xml, verbose_warnings=True)
        self.assertFalse(valid)
        logger_output = "\n".join(cm.output)
        self.assertIn('No language called: "foo"', logger_output)
        self.assertIn('no path from "crx-syl"', logger_output)


if __name__ == "__main__":
    main()
