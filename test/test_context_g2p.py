from unittest import TestCase
import unittest
from readalongs.log import LOGGER

from readalongs.g2p.context_g2p import ContextG2P
from readalongs.g2p.convert_orthography import ConverterLibrary
from lxml import etree



class TestContextG2P(TestCase):
    def setUp(self):
        self.converter = ConverterLibrary()

    
    def test_git(self):
        conversion = self.converter.convert("K̲'ay", "git", "eng-arpabet")
        conversion1 = self.converter.convert('yukwhl', 'git', 'eng-arpabet')
        self.assertEqual(conversion1[0], 'Y UW K W S')
        self.assertEqual(conversion[0], 'K HH AE Y')
        self.assertEqual(conversion[1].composed(), [(2, 1), (3, 4), (4, 7), (5, 9)])


if __name__ == '__main__':
    LOGGER.setLevel('DEBUG')
    unittest.main()