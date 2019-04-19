from unittest import TestCase
import logging

import readalongs
from readalongs.g2p.tokenize_xml import tokenize_xml
from readalongs.g2p.add_ids_to_xml import add_ids
from readalongs.g2p.convert_xml import convert_xml
from lxml import etree

import os, io

EXPECTED_TOKENIZED = io.open(os.path.join(os.path.dirname(__file__),
                              'test_atj_sample_tokenized.xml')).read().strip()
EXPECTED_IDS = io.open(os.path.join(os.path.dirname(__file__),
                              'test_atj_sample_ids.xml')).read().strip()
EXPECTED_CONVERTED = io.open(os.path.join(os.path.dirname(__file__),
                              'test_atj_sample_converted.xml')).read().strip()

class TestAtikamekwG2P(TestCase):
    mapping_dir = os.path.join(next(iter(readalongs.__path__), 'lang'))
    xml = etree.parse(os.path.join(os.path.dirname(__file__),
                                   'test_atj_sample.xml')).getroot()
    def testTokenize(self):
        xml = tokenize_xml(self.xml, self.mapping_dir)
        self.assertEqual(etree.tounicode(xml), EXPECTED_TOKENIZED)

    def testAddIDs(self):
        xml = tokenize_xml(self.xml, self.mapping_dir)
        xml = add_ids(xml)
        self.assertEqual(etree.tounicode(xml), EXPECTED_IDS)

    def testConvert(self):
        xml = tokenize_xml(self.xml, self.mapping_dir)
        xml = add_ids(xml)
        xml = convert_xml(self.mapping_dir, xml)
        self.assertEqual(etree.tounicode(xml), EXPECTED_CONVERTED)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
