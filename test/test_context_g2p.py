from unittest import TestCase
import unittest
from readalongs.log import LOGGER

from g2p import make_g2p
from lxml import etree


class TestG2P(TestCase):
    def setUp(self):
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
             'in_text': 'Qneᴬ',
             'out_text': 'HH N EY'}
        ]

    def test_conversions(self):
        for test in self.test_conversion_data:
            # if test['in_lang'] == 'str-sen':
            #     breakpoint()
            converter = make_g2p(test['in_lang'], test['out_lang'])
            # breakpoint()
            conversion = converter(test['in_text'])
            self.assertEqual(conversion, test['out_text'])

    def test_reduced_indices(self):
        converter = make_g2p('git', 'eng-arpabet')
        conversion = converter("K̲'ay", index=True)
        self.assertEqual(conversion[1].reduced(), [
                         (2, 2), (3, 5), (4, 8), (5, 9)])
        conversion1 = converter("yukwhl", index=True)
        self.assertEqual(conversion1[1].reduced(), [
                         (1, 2), (2, 5), (3, 7), (4, 9), (6, 10)])


if __name__ == '__main__':
    LOGGER.setLevel('DEBUG')
    unittest.main()
