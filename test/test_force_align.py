#!/usr/bin/env python3

"""
Test force-alignment with SoundsSwallower FSG search from Python API
"""

import os
import shutil
import unittest
import wave
from tempfile import TemporaryDirectory

from basic_test_case import BasicTestCase
from lxml import etree
from soundswallower import get_model_path

from readalongs.align import align_audio, convert_to_xhtml, create_input_tei
from readalongs.log import LOGGER
from readalongs.portable_tempfile import PortableNamedTemporaryFile
from readalongs.text.util import load_txt, save_xml


class TestForceAlignment(BasicTestCase):
    """Unit testing suite for forced-alignment with SoundsSwallower"""

    def test_align(self):
        """Basic alignment test case with XML input"""
        xml_path = os.path.join(self.data_dir, "ej-fra.xml")
        wav_path = os.path.join(self.data_dir, "ej-fra.m4a")
        results = align_audio(xml_path, wav_path, unit="w")

        # Verify that the same IDs are in the output
        converted_path = os.path.join(self.data_dir, "ej-fra-converted.xml")
        xml = etree.parse(converted_path).getroot()
        words = results["words"]
        xml_words = xml.xpath(".//w")
        self.assertEqual(len(words), len(xml_words))
        for w, xw in zip(words, xml_words):
            self.assertEqual(xw.attrib["id"], w["id"])

    def test_align_text(self):
        """Basic alignment test case with plain text input"""
        txt_path = os.path.join(self.data_dir, "ej-fra.txt")
        wav_path = os.path.join(self.data_dir, "ej-fra.m4a")
        _, temp_fn = create_input_tei(
            input_file_name=txt_path, text_languages=("fra",), save_temps=None
        )
        results = align_audio(temp_fn, wav_path, unit="w", save_temps=None)

        # Verify that the same IDs are in the output
        converted_path = os.path.join(self.data_dir, "ej-fra-converted.xml")
        xml = etree.parse(converted_path).getroot()
        words = results["words"]
        xml_words = xml.xpath(".//w")
        self.assertEqual(len(words), len(xml_words))
        for w, xw in zip(words, xml_words):
            self.assertEqual(xw.attrib["id"], w["id"])

    def test_align_switch_am(self):
        """Alignment test case with an alternate acoustic model and custom
        noise dictionary."""
        xml_path = os.path.join(self.data_dir, "ej-fra.xml")
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
        converted_path = os.path.join(self.data_dir, "ej-fra-converted.xml")
        xml = etree.parse(converted_path).getroot()
        words = results["words"]
        xml_words = xml.xpath(".//w")
        self.assertEqual(len(words), len(xml_words))
        for w, xw in zip(words, xml_words):
            self.assertEqual(xw.attrib["id"], w["id"])

    def test_align_fail(self):
        """Alignment test case with bad audio that should fail."""
        xml_path = os.path.join(self.data_dir, "ej-fra.xml")
        with PortableNamedTemporaryFile(suffix=".wav") as tf:
            with wave.open(tf, "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(16000)
                writer.writeframes(b"\x00\x00")
            with self.assertRaises(RuntimeError):
                _ = align_audio(xml_path, tf.name, unit="w")


class TestXHTML(BasicTestCase):
    """Test converting the output to xhtml"""

    def test_convert(self):
        """Test converting the output to xhtml"""
        xml_path = os.path.join(self.data_dir, "ej-fra-converted.xml")
        xml = etree.parse(xml_path).getroot()
        convert_to_xhtml(xml)
        with PortableNamedTemporaryFile(suffix=".xml") as tf:
            save_xml(tf.name, xml)
            txt = load_txt(tf.name)
            self.maxDiff = None
            self.assertEqual(
                txt, load_txt(os.path.join(self.data_dir, "ej-fra-converted.xhtml"))
            )


if __name__ == "__main__":
    LOGGER.setLevel("DEBUG")
    unittest.main()
