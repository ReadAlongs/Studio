#!/usr/bin/env python3

from unittest import main, TestCase

from readalongs.log import LOGGER
from readalongs.text.util import (
    compose_indices,
    compose_tiers,
    increment_indices,
    increment_tiers,
)

from g2p import make_g2p
from g2p.mappings import Mapping
from g2p.transducer import Transducer


class TestIndices(TestCase):
    def setUp(self):
        pass

    def test_basic_composition(self):
        mapping = Mapping([{"in": "a", "out": "b"}])
        transducer = Transducer(mapping)
        tg = transducer("abba")
        self.assertEqual(tg.output_string, "bbbb")
        self.assertEqual(tg.edges, [(0, 0), (1, 1), (2, 2), (3, 3)])
        self.assertEqual(tg.edges, compose_indices(tg.edges, tg.edges))

    def test_tiered_composition(self):
        transducer = make_g2p("dan", "eng-arpabet")
        tg = transducer("hej")
        self.assertEqual(tg.output_string, "HH EH Y")
        self.assertEqual(
            tg.edges,
            [
                [(0, 0), (1, 1), (2, 2)],
                [(0, 0), (1, 1), (2, 2)],
                [(0, 0), (0, 1), (0, 2), (1, 3), (1, 4), (1, 5), (2, 6)],
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
                ],
            ],
        )
        self.assertEqual(compose_tiers(tg.edges), [(0, 2), (1, 5), (2, 6)])

    def test_composition_with_none(self):
        transducer = make_g2p("ctp", "eng-arpabet")
        tg = transducer("Qne\u1D2C")
        self.assertEqual(tg.output_string, "HH N EY")
        self.assertEqual(
            tg.edges,
            [
                [(0, 0), (1, 1), (2, 2), (3, None)],
                [(0, 0), (1, 1), (2, 2), (2, 3)],
                [(0, 0), (0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (3, 6)],
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
                ],
            ],
        )
        self.assertEqual(compose_tiers(tg.edges), [(0, 2), (1, 4), (2, 6), (3, 6)])

    def test_fra(self):
        transducer = make_g2p("fra", "eng-arpabet")
        tg = transducer("mais")
        self.assertEqual(tg.output_string, "M EH")
        self.assertEqual(
            compose_tiers(increment_tiers(tg.edges)), [(1, 2), (2, 4), (3, 4), (4, 4)]
        )


if __name__ == "__main__":
    LOGGER.setLevel("DEBUG")
    main()
