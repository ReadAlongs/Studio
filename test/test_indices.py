#!/usr/bin/env python3

from unittest import TestCase, main

from g2p import make_g2p
from g2p.mappings import Mapping
from g2p.transducer import Transducer

from readalongs.log import LOGGER


class TestIndices(TestCase):
    def test_basic_composition(self):
        mapping = Mapping([{"in": "a", "out": "b"}])
        transducer = Transducer(mapping)
        tg = transducer("abba")
        self.assertEqual(tg.output_string, "bbbb")
        self.assertEqual(tg.edges, [(0, 0), (1, 1), (2, 2), (3, 3)])

    def test_tiered_composition(self):
        transducer = make_g2p("dan", "eng-arpabet")
        tg = transducer("hej")
        self.assertEqual(tg.output_string, "HH EH Y ")
        self.assertEqual(
            tg.edges,
            [
                [(0, 0), (1, 1), (2, 2)],
                [(0, 0), (1, 1), (2, 2)],
                [(0, 0), (0, 1), (0, 2), (1, 3), (1, 4), (1, 5), (2, 6), (2, 7)],
            ],
        )
        self.assertEqual(
            tg.pretty_edges(),
            [
                [["h", "h"], ["e", "ɛ"], ["j", "j"]],
                [["h", "h"], ["ɛ", "ɛ"], ["j", "j"]],
                [
                    ["h", "H"],
                    ["h", "H"],
                    ["h", " "],
                    ["ɛ", "E"],
                    ["ɛ", "H"],
                    ["ɛ", " "],
                    ["j", "Y"],
                    ["j", " "],
                ],
            ],
        )

    def test_composition_with_none(self):
        transducer = make_g2p("ctp", "eng-arpabet")
        tg = transducer("Qne\u1D2C")
        self.assertEqual(tg.output_string, "HH N EY ")
        self.assertEqual(
            tg.edges,
            [
                [(0, 0), (1, 1), (2, 2), (3, None)],
                [(0, 0), (1, 1), (2, 2), (2, 3)],
                [(0, 0), (0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (3, 6), (3, 7)],
            ],
        )
        self.assertEqual(
            tg.pretty_edges(),
            [
                [["q", "ʔ"], ["n", "n"], ["e", "e"], ["ᴬ", None]],
                [["ʔ", "ʔ"], ["n", "n"], ["e", "e"], ["e", "ː"]],
                [
                    ["ʔ", "H"],
                    ["ʔ", "H"],
                    ["ʔ", " "],
                    ["n", "N"],
                    ["n", " "],
                    ["e", "E"],
                    ["ː", "Y"],
                    ["ː", " "],
                ],
            ],
        )

    def test_fra(self):
        transducer = make_g2p("fra", "eng-arpabet")
        tg = transducer("mais")
        self.assertEqual(tg.output_string, "M EH ")


if __name__ == "__main__":
    LOGGER.setLevel("DEBUG")
    main()
