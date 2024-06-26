#!/usr/bin/env python

"""Test suite for the readalongs g2p CLI command"""

import os
import re
from unittest import main

from basic_test_case import BasicTestCase
from lxml import etree
from sound_swallower_stub import SoundSwallowerStub
from test_make_xml_cli import updateFormatVersion, updateStudioVersion

from readalongs.align import align_audio
from readalongs.cli import align, g2p, make_xml, tokenize
from readalongs.log import LOGGER
from readalongs.text.convert_xml import convert_xml
from readalongs.text.util import parse_xml


def run_convert_xml(input_string):
    """wrap convert_xml to make unit testing easier"""
    return etree.tounicode(convert_xml(parse_xml(input_string))[0])


def two_xml_elements(xml_text):
    """Extract the opening part of the leading two XML elements in xml_text"""
    return xml_text[: 1 + xml_text.find(">", 1 + xml_text.find(">"))]


class TestG2pCli(BasicTestCase):
    """Test suite for the readalongs g2p CLI command"""

    # Set this to True to display the output of many commands invoked here, for building
    # and debugging this test suite
    show_invoke_output = False

    def test_invoke_g2p(self):
        """Basic invocation of readalongs g2p"""
        input_file = os.path.join(self.data_dir, "fra-tokenized.readalong")
        g2p_file = os.path.join(self.tempdir, "fra-g2p.readalong")
        results = self.runner.invoke(g2p, [input_file, g2p_file])
        # print(f"g2p results.output='{results.output}'")
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, "fra-g2p.readalong")))

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
        input_file = os.path.join(self.data_dir, "mixed-langs.tokenized.readalong")
        g2p_file = os.path.join(self.tempdir, "mixed-langs.g2p.readalong")
        results = self.runner.invoke(g2p, [input_file, g2p_file])
        # print(f"g2p results.output='{results.output}'")
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(g2p_file))

        ref_file = os.path.join(self.data_dir, "mixed-langs.g2p.readalong")
        with open(g2p_file, encoding="utf8") as output_f, open(
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
                f"output {g2p_file} and reference {ref_file} differ.",
            )

    def test_invoke_with_obsolete_switches(self):
        """Using obsolete options should yield a helpful error message"""

        input_file = os.path.join(self.data_dir, "fra-tokenized.readalong")
        g2p_file = os.path.join(self.tempdir, "obsolete1.readalong")
        results = self.runner.invoke(
            g2p, ["--g2p-fallback", "fra:und", input_file, g2p_file]
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("is obsolete", results.output)

        g2p_file = os.path.join(self.tempdir, "obsolete2.readalong")
        results = self.runner.invoke(g2p, ["--g2p-verbose", input_file, g2p_file])
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("is obsolete", results.output)

    # Write text to a temp file, pass it through make-xml -l lang, and then tokenize,
    # saving the final results into filename.
    # filename is assumed to be inside self.tempdir, so we count on tearDown() to clean up.
    def write_make_xml_tokenize(self, text, lang, filename):
        """Create the input file for some test cases in this suite"""
        with open(filename + ".input.txt", "w", encoding="utf8") as f:
            print(text, file=f)
        self.runner.invoke(
            make_xml,
            [
                "-l",
                lang,
                "--lang-no-append-und",
                filename + ".input.txt",
                filename + ".prepared.readalong",
            ],
        )
        self.runner.invoke(tokenize, [filename + ".prepared.readalong", filename])

    def test_english_oov(self):
        """readalongs g2p should handle English OOVs correctly"""
        tok_file = os.path.join(self.tempdir, "tok.readalong")
        self.write_make_xml_tokenize("This is a froobnelicious OOV.", "eng", tok_file)
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
        tok_file_with_fallback = os.path.join(self.tempdir, "fallback.readalong")
        self.write_make_xml_tokenize(
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
        tok_file = os.path.join(self.tempdir, "tok.readalong")
        g2p_file = os.path.join(self.tempdir, "g2p.readalong")
        self.write_make_xml_tokenize(
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
        tok_file2 = os.path.join(self.tempdir, "tok2.readalong")
        self.write_make_xml_tokenize(
            "Le ñ n'est pas dans l'alphabet français.", "fra:und", tok_file2
        )
        g2p_file2 = os.path.join(self.tempdir, "g2p-fallback.readalong")
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
        tok_file = os.path.join(self.tempdir, "text.tokenized.readalong")
        g2p_file = os.path.join(self.tempdir, "text.g2p.readalong")
        self.write_make_xml_tokenize(
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
        tok_file2 = os.path.join(self.tempdir, "text.tokenized2.readalong")
        self.write_make_xml_tokenize(
            "In French été works but Nunavut ᓄᓇᕗᑦ does not.", "eng:und", tok_file2
        )
        results = self.runner.invoke(g2p, [tok_file2, "-"])
        self.assertEqual(results.exit_code, 0)
        self.assertIn("Trying fallback: Und", results.output)

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
                    "--debug-g2p",
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
        self.assertIn("Trying fallback: French", results.output)
        self.assertIn("Trying fallback: Inuktitut", results.output)
        self.assertNotIn("could not be g2p", results.output)
        self.assertIn("Number of aligned segments", results.output)

    def test_with_stdin(self):
        """readalongs g2p running with stdin as input"""
        input_file = os.path.join(self.data_dir, "fra-tokenized.readalong")
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
        input_file = os.path.join(self.tempdir, "pre-g2p.readalong")
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
        text_file = os.path.join(self.data_dir, "mixed-langs.tokenized.readalong")
        audio_file = os.path.join(self.data_dir, "ej-fra.m4a")
        # bogus alignments but they must all exist!!!
        with SoundSwallowerStub(
            "t0b0d0p0s0w0:1:2",
            "t0b0d0p0s0w1:2:3",
            "t0b0d0p0s0w2:3:4",
            "t0b0d0p0s0w3:4:5",
            "t0b0d0p0s1w0:5:6",
            "t0b0d0p0s1w1:6:7",
            "t0b0d0p0s1w2:7:8",
            "t0b0d0p0s1w3:8:9",
            "t0b0d0p0s2w0:9:10",
            "t0b0d0p0s2w1:10:11",
            "t0b0d0p0s2w2:11:12",
            "t0b0d0p0s2w3:12:13",
            "t0b0d0p0s3w0:13:14",
            "t0b0d0p0s3w1:14:15",
            "t0b0d0p0s3w2:15:16",
            "t0b0d0p0s3w3:16:17",
        ):
            _ = align_audio(
                text_file, audio_file, save_temps=os.path.join(self.tempdir, "foo")
            )
        with open(os.path.join(self.tempdir, "foo.dict"), "r", encoding="utf8") as f:
            dict_file = f.read()
            self.assertIn("S AH S IY", dict_file)  # "ceci" in fra
            self.assertIn("DH IH S", dict_file)  # "this" in eng
            self.assertIn("HH EH Y", dict_file)  # "Hej" in dan
            self.assertIn("D G IY T UW P IY D", dict_file)  # pre-g2p'd OOV

    def test_convert_xml(self):
        """unit testing for readalongs.text.convert_xml.convert_xml()

        convert_xml() is the inner method in readalongs that calls g2p.
        It's not very well named, but it still needs unit testing. :)
        """
        self.assertEqual(
            run_convert_xml("<t><w>word</w><w></w><n>not word</n></t>"),
            '<t><w ARPABET="W OW D D">word</w><w/><n>not word</n></t>',
        )

        self.assertEqual(
            run_convert_xml(
                '<s><w xml:lang="eng">Patrick</w><w xml:lang="kwk-umista">xtła̱n</w></s>'
            ),
            '<s><w xml:lang="eng" ARPABET="P AE T R IH K">Patrick</w>'
            '<w xml:lang="kwk-umista" ARPABET="K Y T S AH N">xtła̱n</w></s>',
        )

        self.assertEqual(
            run_convert_xml('<s><w xml:lang="und">Patrickxtła̱n</w></s>'),
            '<s><w xml:lang="und" ARPABET="P AA T D IY CH K K T L AA N">Patrickxtła̱n</w></s>',
        )

    def test_convert_xml_with_newlines(self):
        """Newlines inside words are weird, but they should not cause errors"""

        def compact_arpabet(xml_string: str) -> str:
            etree_root = parse_xml(xml_string)
            arpabet = etree_root[0].attrib["ARPABET"]
            return re.sub(r"\s+", " ", arpabet)

        converted_1 = run_convert_xml(
            """<s><w>
               <part>first part of the word</part>
               <part>second part of the word</part>
               </w></s>"""
        )
        converted_2 = run_convert_xml(
            "<s><w><part>first part of the word</part><part>second part of the word</part></w></s>"
        )
        self.assertEqual(compact_arpabet(converted_1), compact_arpabet(converted_2))

    def test_convert_xml_subwords(self):
        """Unit testing for reintroducing subword units"""
        self.assertEqual(
            run_convert_xml(
                '<s><w><part xml:lang="eng">Patrick</part><part xml:lang="kwk-umista">xtła̱n</part></w></s>'
            ),
            '<s><w ARPABET="P AE T R IH K K Y T S AH N"><part xml:lang="eng">Patrick</part>'
            '<part xml:lang="kwk-umista">xtła̱n</part></w></s>',
        )

        self.assertEqual(
            run_convert_xml(
                '<s><w>foo<syl xml:lang="eng">Patrick</syl>bar<syl xml:lang="kwk-umista">xtła̱n</syl>baz</w></s>'
            ),
            '<s><w ARPABET="F OW OW P AE T R IH K B AA D K Y T S AH N B AA Z">'
            'foo<syl xml:lang="eng">Patrick</syl>bar<syl xml:lang="kwk-umista">xtła̱n</syl>baz</w></s>',
        )

        converted_by_syllable = run_convert_xml(
            '<s><w xml:lang="und"><syl>abc</syl><syl>def</syl><syl>ghi</syl></w></s>'
        )
        converted_as_a_whole = run_convert_xml('<s><w xml:lang="und">abcdefghi</w></s>')
        self.assertEqual(
            two_xml_elements(converted_by_syllable),
            two_xml_elements(converted_as_a_whole),
        )

        moh_eg_with_highlights = "<s xml:lang='moh'><w><span class='pronoun'>tati</span><span class='root'>atkèn:se</span><span class='aspect'>hkwe'</span></w></s>"
        moh_eg_merged = "<s xml:lang='moh'><w>tatiatkèn:sehkwe'</w></s>"
        self.assertEqual(two_xml_elements(moh_eg_merged), "<s xml:lang='moh'><w>")
        self.assertEqual(
            two_xml_elements(run_convert_xml(moh_eg_with_highlights)),
            two_xml_elements(run_convert_xml(moh_eg_merged)),
        )

        moh_example_input_full = """
            <document xml:lang='moh'>
              <s>
                <w>
                  <span class='pronoun'>tati</span>
                  <span class='root'>atkèn:se</span>
                  <span class='aspect'>hkwe'</span>
                </w>
              </s>
            </document>"""
        _ = run_convert_xml(moh_example_input_full)

        example_with_fallback_lang = """
            <document xml:lang="fra" fallback-langs="dan"><s>
              <w><part lang="fra">ceci</part><part lang="iku">not_really_iku</part></w>
            </s></document>"""
        with self.assertLogs(LOGGER, level="WARNING") as cm:
            result = run_convert_xml(example_with_fallback_lang)
        self.assertIn("S AH S IY N AO T _ZH EH AE L L UW _IY K UW", result)
        logger_output = "\n".join(cm.output)
        self.assertIn(
            'No valid g2p conversion found for "not_really_iku"', logger_output
        )

    def test_convert_xml_invalid(self):
        """test readalongs.text.convert_xml.convert_xml() with invalid input"""
        xml = parse_xml('<s><w ARPABET="V AA L IY D">valid</w></s>')
        c_xml, valid = convert_xml(xml)
        self.assertEqual(
            etree.tounicode(c_xml), '<s><w ARPABET="V AA L IY D">valid</w></s>'
        )
        self.assertTrue(valid, "convert_xml with valid pre-g2p'd text")

        xml = parse_xml('<s><w ARPABET="invalid">invalid</w></s>')
        c_xml, valid = convert_xml(xml)
        self.assertEqual(
            etree.tounicode(c_xml), '<s><w ARPABET="invalid">invalid</w></s>'
        )
        self.assertFalse(valid, "convert_xml with invalid pre-g2p'd text")

    def test_invalid_langs_in_xml(self):
        xml = parse_xml(
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
        self.assertIn("No lang", logger_output)
        self.assertIn("foo", logger_output)
        self.assertIn('no path from "crx-syl"', logger_output)


if __name__ == "__main__":
    main()
