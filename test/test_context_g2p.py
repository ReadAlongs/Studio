from unittest import TestCase
import unittest
from readalongs.log import LOGGER

from readalongs.g2p.context_g2p import ContextG2P
from readalongs.g2p.convert_orthography import ConverterLibrary
from lxml import etree


class TestContextG2P(TestCase):
    def setUp(self):
        self.converter = ConverterLibrary()
        self.test_conversion_data = [
            {'in_lang': 'git',
             'out_lang': 'eng-arpabet',
             'in_text': "K̲'ay",
             'out_text': 'K HH AE Y'},
            {'in_lang': 'git',
             'out_lang': 'eng-arpabet',
             'in_text': "guts'uusgi'y",
             'out_text': 'G UW T S HH UW S G IY HH Y'},
            {'in_lang': 'str-sen',
             'out_lang': 'eng-arpabet',
             'in_text': 'X̱I¸ÁM¸',
             'out_text': 'SH W IY HH EY M HH'},
            {'in_lang': 'ctp',
             'out_lang': 'eng-arpabet',
             'in_text': 'unᴬ',
             'out_text': 'UW N'}
        ]

    def test_conversions(self):
        for test in self.test_conversion_data:
            # if test['in_lang'] == 'str-sen':
            #     breakpoint()
            conversion = self.converter.convert(
                test['in_text'], test['in_lang'], test['out_lang'])
            self.assertEqual(conversion[0], test['out_text'])

    def test_reduced_indices(self):
        conversion = self.converter.convert("K̲'ay", "git", "eng-arpabet")
        self.assertEqual(conversion[1].reduced(), [
                         (2, 1), (3, 4), (4, 7), (5, 9)])
        conversion1 = self.converter.convert("yukwhl", 'git', 'eng-arpabet')
        self.assertEqual(conversion1[1].reduced(), [
                         (1, 1), (2, 4), (3, 6), (4, 8), (6, 10)])


if __name__ == '__main__':
    LOGGER.setLevel('DEBUG')
    unittest.main()
