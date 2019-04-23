"""
Test force-alignment with PocketSphinx FSG search from Python API
"""

import unittest
import logging
import tempfile
import os
from lxml import etree

from readalongs.align import align_audio, create_input_xml, convert_to_xhtml
from readalongs.g2p.util import save_xml, load_txt


class TestForceAlignment(unittest.TestCase):
    logging.basicConfig(level=logging.DEBUG)
    data_dir = os.path.dirname(__file__)

    def testAlign(self):
        xml_path = os.path.join(self.data_dir, 'test_atj_sample.xml')
        wav_path = os.path.join(self.data_dir, 'test_atj_sample.wav')
        results = align_audio(xml_path, wav_path, unit='w')

        # Verify that the same IDs are in the output
        converted_path = os.path.join(
            self.data_dir, 'test_atj_sample_converted.xml')
        xml = etree.parse(converted_path).getroot()
        words = results['words']
        xml_words = xml.xpath(".//w")
        self.assertEqual(len(words), len(xml_words))
        for w, xw in zip(words, xml_words):
            self.assertEqual(xw.attrib['id'], w['id'])

    def testAlignText(self):
        txt_path = os.path.join(self.data_dir, 'test_atj_sample.txt')
        wav_path = os.path.join(self.data_dir, 'test_atj_sample.wav')
        tempfile = create_input_xml(txt_path, 'atj')
        results = align_audio(tempfile.name, wav_path, unit='w')

        # Verify that the same IDs are in the output
        converted_path = os.path.join(
            self.data_dir, 'test_atj_sample_converted.xml')
        xml = etree.parse(converted_path).getroot()
        words = results['words']
        xml_words = xml.xpath(".//w")
        self.assertEqual(len(words), len(xml_words))
        for w, xw in zip(words, xml_words):
            self.assertEqual(xw.attrib['id'], w['id'])


class TestXHTML(unittest.TestCase):
    data_dir = os.path.dirname(__file__)

    def testConvert(self):
        xml_path = os.path.join(self.data_dir, 'test_atj_sample_tokenized.xml')
        xml = etree.parse(xml_path).getroot()
        convert_to_xhtml(xml)
        with tempfile.NamedTemporaryFile(suffix='.xml') as tf:
            save_xml(tf.name, xml)
            txt = load_txt(tf.name)
            self.maxDiff = None
            self.assertEqual(txt,
                             load_txt(
                                 os.path.join(self.data_dir,
                                              'test_atj_sample_tokenized.xhtml')))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
