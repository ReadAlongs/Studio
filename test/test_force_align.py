#!/usr/bin/env python

"""
Test force-alignment with SoundSwallower FSG search from Python API
"""

import os
import shutil
import unittest
import wave
from tempfile import TemporaryDirectory

from basic_test_case import BasicTestCase
from lxml import etree
from soundswallower import get_model_path

from readalongs.align import (
    align_audio,
    convert_to_xhtml,
    create_input_ras,
    get_word_texts_and_sentences,
)
from readalongs.log import LOGGER
from readalongs.portable_tempfile import PortableNamedTemporaryFile
from readalongs.text.util import load_txt, load_xml, save_xml


class TestForceAlignment(BasicTestCase):
    """Unit testing suite for forced-alignment with SoundSwallower"""

    def test_align(self):
        """Basic alignment test case with XML input"""
        xml_path = os.path.join(self.data_dir, "ej-fra.readalong")
        wav_path = os.path.join(self.data_dir, "ej-fra.m4a")
        results = align_audio(xml_path, wav_path, unit="w", debug_aligner=True)

        # Verify that the same IDs are in the output
        converted_path = os.path.join(self.data_dir, "ej-fra-converted.readalong")
        xml = load_xml(converted_path)
        words = results["words"]
        xml_words = xml.xpath(".//w")
        self.assertEqual(len(words), len(xml_words))
        for w, xw in zip(words, xml_words):
            self.assertEqual(xw.attrib["id"], w["id"])

    def test_align_text(self):
        """Basic alignment test case with plain text input"""
        txt_path = os.path.join(self.data_dir, "ej-fra.txt")
        wav_path = os.path.join(self.data_dir, "ej-fra.m4a")
        _, temp_fn = create_input_ras(
            input_file_name=txt_path, text_languages=("fra",), save_temps=None
        )
        results = align_audio(temp_fn, wav_path, unit="w", save_temps=None)

        # Verify that the same IDs are in the output
        converted_path = os.path.join(self.data_dir, "ej-fra-converted.readalong")
        xml = load_xml(converted_path)
        words = results["words"]
        xml_words = xml.xpath(".//w")
        self.assertEqual(len(words), len(xml_words))
        for w, xw in zip(words, xml_words):
            self.assertEqual(xw.attrib["id"], w["id"])

        # White-box testing to make sure srt, TextGrid and vtt output will have the
        # sentences collected correctly.
        words, sentences = get_word_texts_and_sentences(
            results["words"], results["tokenized"]
        )
        self.assertEqual(len(sentences), 7)
        self.assertEqual(len(words), 99)

        def make_element(tag, text="", tail=""):
            """Convenient Element constructor wrapper"""
            el = etree.Element(tag)
            el.text = text
            el.tail = tail
            return el

        # Do some word doctoring to make sure sub-word units don't cause trouble
        # This might be nicer in a different test case, but I want to reuse
        # results from the call above, so I'm glomming it on here...
        xml = results["tokenized"]
        for i, word_el in enumerate(xml.xpath(".//w")):
            if i == 1:
                # Modify the <w>
                word_el.text += " stuff"
            elif i == 2:
                # Whole <w> text in one <subw>
                word_el.text = ""
                word_el.append(make_element("subw", "subwordtext"))
            elif i == 3:
                # <w> with three clean <syl> elements
                word_el.text = ""
                for i in range(3):
                    word_el.append(make_element("syl", "syl;"))
            elif i == 4:
                # Messy <w> is still valid structure
                word_el.text = "head text;"
                word_el.append(make_element("syl", "syllable text;", "syl tail;"))
                word_el.tail = "tail from the word itself is ignored;"
                # etree.dump(word_el)
            elif i == 5:
                # Nested sub elements
                word_el.append(make_element("syl", "syl;", "tail;"))
                word_el[0].append(make_element("subsyl", "sub;"))
                word_el.append(make_element("syl", "another syl;"))
                break
        _, sentences = get_word_texts_and_sentences(
            results["words"], results["tokenized"]
        )
        self.assertEqual(
            [w["text"] for w in sentences[1]],
            [
                "Je stuff",
                "subwordtext",
                "syl;syl;syl;",
                "head text;syllable text;syl tail;",
                "Joanissyl;sub;tail;another syl;",
            ],
        )

    def test_align_switch_am(self):
        """Alignment test case with an alternate acoustic model and custom
        noise dictionary."""
        xml_path = os.path.join(self.data_dir, "ej-fra.readalong")
        wav_path = os.path.join(self.data_dir, "ej-fra.m4a")
        # Try with some extra stuff in the noisedict
        with TemporaryDirectory(prefix="readalongs_am_") as tempdir:
            custom_am_path = os.path.join(tempdir, "en-us")
            shutil.copytree(get_model_path("en-us"), custom_am_path)
            with open(os.path.join(custom_am_path, "noisedict"), "at") as fh:
                fh.write(";; here is a comment\n")
                fh.write("[BOGUS] SIL\n")
            results = align_audio(
                xml_path, wav_path, unit="w", config={"acoustic_model": custom_am_path}
            )
            # Try with no noisedict
            os.remove(os.path.join(custom_am_path, "noisedict"))
            results = align_audio(
                xml_path, wav_path, unit="w", config={"acoustic_model": custom_am_path}
            )
        # Verify that the same IDs are in the output
        converted_path = os.path.join(self.data_dir, "ej-fra-converted.readalong")
        xml = load_xml(converted_path)
        words = results["words"]
        xml_words = xml.xpath(".//w")
        self.assertEqual(len(words), len(xml_words))
        for w, xw in zip(words, xml_words):
            self.assertEqual(xw.attrib["id"], w["id"])

    def test_align_fail(self):
        """Alignment test case with bad audio that should fail."""
        xml_path = os.path.join(self.data_dir, "ej-fra.readalong")
        with PortableNamedTemporaryFile(suffix=".wav") as tf:
            with wave.open(tf, "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(16000)
                writer.writeframes(b"\x00\x00")
            with self.assertRaises(RuntimeError):
                _ = align_audio(xml_path, tf.name, unit="w")

    def test_bad_align_mode(self):
        with self.assertRaises(AssertionError):
            _ = align_audio(
                os.path.join(self.data_dir, "ej-fra.readalong"),
                os.path.join(self.data_dir, "noise.mp3"),
                alignment_mode="invalid-mode",
            )


class TestXHTML(BasicTestCase):
    """Test converting the output to xhtml"""

    def test_convert(self):
        """Test converting the output to xhtml"""
        xml_path = os.path.join(self.data_dir, "ej-fra-converted.readalong")
        xml = load_xml(xml_path)
        convert_to_xhtml(xml)
        with PortableNamedTemporaryFile(suffix=".readalong") as tf:
            save_xml(tf.name, xml)
            txt = load_txt(tf.name)
            self.maxDiff = None
            self.assertEqual(
                txt, load_txt(os.path.join(self.data_dir, "ej-fra-converted.xhtml"))
            )

    def test_convert_no_version(self):
        xml_path = os.path.join(self.data_dir, "ej-fra-converted.readalong")
        xml = load_xml(xml_path)
        del xml.attrib["version"]
        convert_to_xhtml(xml)
        with PortableNamedTemporaryFile(suffix=".readalong") as tf:
            save_xml(tf.name, xml)
            txt = load_txt(tf.name)
            self.maxDiff = None
            self.assertEqual(
                txt, load_txt(os.path.join(self.data_dir, "ej-fra-converted.xhtml"))
            )


if __name__ == "__main__":
    LOGGER.setLevel("DEBUG")
    unittest.main()
