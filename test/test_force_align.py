"""
Test force-alignment with PocketSphinx FSG search from Python API
"""

import unittest
import logging
import os
from lxml import etree

from readalongs.align import align_audio, create_input_xml

class TestForceAlignment(unittest.TestCase):
    logging.basicConfig(level=logging.DEBUG)
    data_dir = os.path.dirname(__file__)
    def testAlign(self):
        xml_path = os.path.join(self.data_dir, 'test_atj_sample.xml') 
        wav_path = os.path.join(self.data_dir, 'test_atj_sample.wav')
        results = align_audio(xml_path, wav_path, unit='w')

        # Verify that the same IDs are in the output
        converted_path = os.path.join(self.data_dir, 'test_atj_sample_converted.xml') 
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
        converted_path = os.path.join(self.data_dir, 'test_atj_sample_converted.xml') 
        xml = etree.parse(converted_path).getroot()
        words = results['words']
        xml_words = xml.xpath(".//w")
        self.assertEqual(len(words), len(xml_words))
        for w, xw in zip(words, xml_words):
            self.assertEqual(xw.attrib['id'], w['id'])

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
